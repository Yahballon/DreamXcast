#!/usr/bin/env bash
# Reproduce the PSFlycast v1.1.0 RADV PS5 toolchain in this app's build dir.
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
work="$root/build"
mkdir -p "$work"
cd "$work"
clone_if_missing() {
  if [[ ! -d "$1/.git" ]]; then git clone "$2" "$1"; fi
}
clone_if_missing PS5_VulkanTemplate https://github.com/mihawk-99/PS5_VulkanTemplate.git
clone_if_missing PS5_Vulkan https://github.com/mihawk-99/PS5_Vulkan.git
clone_if_missing PS5_Mesa https://github.com/mihawk-99/PS5_Mesa.git
clone_if_missing PS5_PayloadSDK https://github.com/mihawk-99/PS5_PayloadSDK.git
clone_if_missing libsmb2 https://github.com/sahlberg/libsmb2.git
git -C PS5_Vulkan checkout --detach 5b5e4fc2d80fdb67a4f61ba9e6a8a424026bb8a5
git -C libsmb2 checkout --detach 7e4ff97cf00edb288b6b763888e4326842afdc76
if [[ ! -f PS5_Mesa/.dreamcastx-patched ]]; then
  git -C PS5_Mesa checkout -B dreamcastx-patches 7b59ef27c1b09b9671bc4153c41940c3155c3af2
  # git am creates real commits, even on clean ephemeral Actions runners.
  # Configure the identity only inside this dependency checkout.
  git -C PS5_Mesa config user.name "PS5DreamcastX CI"
  git -C PS5_Mesa config user.email "ps5-dreamcastx-ci@users.noreply.github.com"
  git -C PS5_Mesa am "$work/flycast/shell/ps5/mesa/"*.patch
  touch PS5_Mesa/.dreamcastx-patched
fi
sed -i "s/^mesa_revision=.*/mesa_revision=$(git -C PS5_Mesa rev-parse HEAD)/" PS5_Vulkan/tools/build-radv.sh
export PS5_VULKAN_DIR="$work/PS5_Vulkan"
export PS5_MESA_FORK="$work/PS5_Mesa"
export PS5_PAYLOAD_SDK_FORK="$work/PS5_PayloadSDK"
# Bootstrap only the toolchain the PS5 title actually uses; no console IP,
# controller payload, FTP access, or unrelated demo app is needed in CI.
(
  cd "$work/PS5_Vulkan"
  bash tools/setup-native-dependencies.sh
  # The PS5_Vulkan demo app may fail before RADV is available. Its
  # native link tool and libc.prx are the only make outputs we require.
  if ! make > "$work/ps5-vulkan-prepare.log" 2>&1; then
    if [[ ! -x build/host/ps5-native-tool || ! -s runtime/libc.prx ]]; then
      tail -n 100 "$work/ps5-vulkan-prepare.log" >&2
      exit 1
    fi
    echo "Vulkan native tools ready; optional demo app skipped"
  fi
  bash tools/build-radv.sh release
)
git -C PS5_VulkanTemplate submodule update --init external/glm
bash PS5_VulkanTemplate/ps5/tools/setup-sdk.sh

test -s "$work/PS5_Vulkan/.deps/native/radv-release/lib/libvulkan_radeon.ps5.a"
test -s "$work/PS5_Vulkan/runtime/libc.prx"
test -x "$work/PS5_Vulkan/build/host/ps5-native-tool"

# Reuse the exact PS5_VulkanTemplate SDK pin built by bootstrap.sh.
# The previous independent SDK checkout was redundant and out of sync.
sdk="$work/PS5_VulkanTemplate/.deps/native/ps5-payload-sdk"
test -x "$sdk/bin/prospero-clang++"
test -s "$sdk/target/lib/libps5platform.a"
# Preserve the original workflow's SDK location for any existing callers.
mkdir -p "$work/sdk-dreamcastx"
ln -sfn "$sdk" "$work/sdk-dreamcastx/ps5-payload-sdk"
echo "PS5 native dependencies ready (SDK: $sdk)"
