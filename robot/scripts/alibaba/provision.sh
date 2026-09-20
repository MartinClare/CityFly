#!/bin/bash
# Create the City Fly robot box in Alibaba Cloud Hong Kong.
# Requires: aliyun CLI configured (`aliyun configure`) with ECS + VPC rights.
set -euo pipefail

REGION="${REGION:-cn-hongkong}"
NAME="${NAME:-city-fly-robot}"
INSTANCE_TYPE="${INSTANCE_TYPE:-ecs.t6-c1m2.large}"
DISK_GB="${DISK_GB:-40}"
SSH_PUB="${SSH_PUB:-$HOME/.ssh/id_ed25519.pub}"
KEY_NAME="${KEY_NAME:-city-fly}"
MY_IP="${MY_IP:-$(curl -fsS https://api.ipify.org)}"

need() { command -v "$1" >/dev/null || { echo "missing $1" >&2; exit 1; }; }
need aliyun
need curl
need python3

if [[ ! -f "$SSH_PUB" ]]; then
  echo "No SSH public key at $SSH_PUB" >&2
  exit 1
fi

if ! aliyun configure list >/dev/null 2>&1; then
  echo "Run: aliyun configure   (region cn-hongkong)" >&2
  exit 1
fi

echo "Region=$REGION  type=$INSTANCE_TYPE  SSH from $MY_IP/32"

vpc_id="$(aliyun ecs DescribeVpcs --RegionId "$REGION" --output cols=VpcId,IsDefault rows=Vpcs.Vpc[] 2>/dev/null | awk 'NR==2{print $1}')"
if [[ -z "${vpc_id:-}" || "$vpc_id" == "VpcId" ]]; then
  echo "Creating default-style VPC..."
  vpc_id="$(aliyun vpc CreateVpc --RegionId "$REGION" --CidrBlock 10.20.0.0/16 --VpcName city-fly-vpc --query VpcId --output tsv)"
  echo "Waiting for VPC $vpc_id"
  for _ in $(seq 1 30); do
    st="$(aliyun vpc DescribeVpcs --RegionId "$REGION" --VpcId "$vpc_id" --query 'Vpcs.Vpc[0].Status' --output tsv 2>/dev/null || true)"
    [[ "$st" == "Available" ]] && break
    sleep 2
  done
fi
echo "VPC $vpc_id"

vsw_id="$(aliyun vpc DescribeVSwitches --RegionId "$REGION" --VpcId "$vpc_id" --query 'VSwitches.VSwitch[0].VSwitchId' --output tsv)"
if [[ -z "${vsw_id:-}" || "$vsw_id" == "None" ]]; then
  zone="$(aliyun ecs DescribeAvailableResource --RegionId "$REGION" --DestinationResource InstanceType --InstanceType "$INSTANCE_TYPE" --query 'AvailableZones.AvailableZone[0].ZoneId' --output tsv)"
  vsw_id="$(aliyun vpc CreateVSwitch --RegionId "$REGION" --ZoneId "$zone" --CidrBlock 10.20.0.0/24 --VpcId "$vpc_id" --VSwitchName city-fly-vsw --query VSwitchId --output tsv)"
  echo "Waiting for vSwitch $vsw_id"
  sleep 5
fi
echo "vSwitch $vsw_id"

sg_id="$(aliyun ecs DescribeSecurityGroups --RegionId "$REGION" --VpcId "$vpc_id" --query "SecurityGroups.SecurityGroup[?SecurityGroupName=='city-fly-sg'].SecurityGroupId | [0]" --output tsv 2>/dev/null || true)"
if [[ -z "${sg_id:-}" || "$sg_id" == "None" ]]; then
  sg_id="$(aliyun ecs CreateSecurityGroup --RegionId "$REGION" --VpcId "$vpc_id" --SecurityGroupName city-fly-sg --Description "City Fly robot SSH only" --query SecurityGroupId --output tsv)"
  aliyun ecs AuthorizeSecurityGroup --RegionId "$REGION" --SecurityGroupId "$sg_id" \
    --IpProtocol tcp --PortRange 22/22 --SourceCidrIp "${MY_IP}/32" --Description "ssh from editor"
fi
echo "Security group $sg_id"

if ! aliyun ecs DescribeKeyPairs --RegionId "$REGION" --KeyPairName "$KEY_NAME" --query 'KeyPairs.KeyPair[0].KeyPairName' --output tsv 2>/dev/null | grep -q "$KEY_NAME"; then
  aliyun ecs ImportKeyPair --RegionId "$REGION" --KeyPairName "$KEY_NAME" --PublicKeyBody "$(cat "$SSH_PUB")"
  echo "Imported key pair $KEY_NAME"
fi

# Hong Kong trial catalog often ships 22.04 only.
image_id="$(aliyun ecs DescribeImages --RegionId "$REGION" --ImageOwnerAlias system --OSType linux \
  --query "Images.Image[?contains(ImageName, 'ubuntu_22_04') && contains(ImageName, 'x64')].ImageId | [0]" --output tsv)"
if [[ -z "${image_id:-}" || "$image_id" == "None" ]]; then
  image_id="$(aliyun ecs DescribeImages --RegionId "$REGION" --ImageOwnerAlias system --OSType linux \
    --query "Images.Image[?contains(ImageName, 'ubuntu_24_04') && contains(ImageName, 'x64')].ImageId | [0]" --output tsv)"
fi
echo "Image $image_id"

existing="$(aliyun ecs DescribeInstances --RegionId "$REGION" --InstanceName "$NAME" \
  --query 'Instances.Instance[0].InstanceId' --output tsv 2>/dev/null || true)"
if [[ -n "${existing:-}" && "$existing" != "None" ]]; then
  iid="$existing"
  echo "Instance already exists: $iid"
else
  iid="$(aliyun ecs RunInstances --RegionId "$REGION" \
    --ImageId "$image_id" \
    --InstanceType "$INSTANCE_TYPE" \
    --SecurityGroupId "$sg_id" \
    --VSwitchId "$vsw_id" \
    --InstanceName "$NAME" \
    --HostName cityfly \
    --InternetMaxBandwidthOut 10 \
    --InternetChargeType PayByTraffic \
    --KeyPairName "$KEY_NAME" \
    --InstanceChargeType PostPaid \
    --SystemDisk.Category cloud_essd \
    --SystemDisk.Size "$DISK_GB" \
    --query 'InstanceIdSets.InstanceIdSet[0]' --output tsv)"
  echo "Created $iid — waiting for Running"
  aliyun ecs StartInstance --InstanceId "$iid" >/dev/null 2>&1 || true
  for _ in $(seq 1 40); do
    st="$(aliyun ecs DescribeInstances --RegionId "$REGION" --InstanceIds "[\"$iid\"]" --query 'Instances.Instance[0].Status' --output tsv)"
    [[ "$st" == "Running" ]] && break
    sleep 5
  done
fi

ip="$(aliyun ecs DescribeInstances --RegionId "$REGION" --InstanceIds "[\"$iid\"]" --query 'Instances.Instance[0].PublicIpAddress.IpAddress[0]' --output tsv)"
if [[ -z "${ip:-}" || "$ip" == "None" ]]; then
  eip="$(aliyun vpc AllocateEipAddress --RegionId "$REGION" --Bandwidth 10 --InternetChargeType PayByTraffic --query AllocationId --output tsv)"
  aliyun vpc AssociateEipAddress --RegionId "$REGION" --AllocationId "$eip" --InstanceId "$iid" --InstanceType EcsInstance
  ip="$(aliyun vpc DescribeEipAddresses --RegionId "$REGION" --AllocationId "$eip" --query 'EipAddresses.EipAddress[0].IpAddress' --output tsv)"
fi

state_dir="$(cd "$(dirname "$0")" && pwd)/.state"
mkdir -p "$state_dir"
cat > "$state_dir/host.env" <<EOF
CITYFLY_HOST=$ip
CITYFLY_USER=root
CITYFLY_INSTANCE=$iid
CITYFLY_REGION=$REGION
EOF
echo "Ready: root@$ip"
echo "Next: scripts/alibaba/sync.sh --bootstrap"
