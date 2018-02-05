#!/bin/bash

BORG_BACKUP_PATH="/mnt/external1/backups"
BORG_COMPRESSION="auto,zstd"
BORG_FLAGS="-x -s"
#BORG_FLAGS="-x -s --progress"
BORG_PASSPHRASE="${BORG_PASSPHRASE}"
BORG_ENCRYPTION="repokey-blake2"

export BORG_PASSPHRASE
declare -A snapper_lv_snapshots snapper_mounted

(( EUID == 0 )) || { echo "This script must be run as root"; exit 1; }

# check sudo
# sudo -v || { echo "Needs sudo" ; exit 1; }

# Get configured snapper filesystems
snapper_filesystems=($( snapper list-configs | awk 'NR > 2 { print $3 }' ))
snapper_configs=($( snapper list-configs | awk 'NR>2 { print $1 }' ))
snapper_devices=($(
    for mount in "${snapper_filesystems[@]}"; do
        __df_output=($( df -l --no-sync --output=source "$mount" ))
        echo "${__df_output[1]}"
    done
))

get_latest() {
    local config="$1"
    for i in "${!snapper_configs[@]}"; do
        if [[ "${snapper_configs[i]}" == "$config" ]]; then
            local device="${snapper_devices[i]##*/}"
            local snapshots="${snapper_lv_snapshots[$device]}"
            # shellcheck disable=2155
            local latest=$( tail -n1 <<< "$snapshots" )
            echo "${latest#*-snapshot}"
        fi
    done
}

mount_snapshot() {
    local config="$1"
    local type="$2"
    local snapshot_num="$3"
    snapper -c "$config" "$type" "$snapshot_num"
}

borg_create_snap() {
    local config="$1"
    local num="$2"
    local mount="$3"
    # shellcheck disable=2086
    borg create ${BORG_FLAGS} \
        ${BORG_COMPRESSION:+-C ${BORG_COMPRESSION}} \
        "${BORG_BACKUP_PATH}/${config}::${config}-snapshot${num}" "$mount"
}

borg_create_repo() {
    local config="$1"
    local num="$2"
    local mount="$3"
    borg init \
        -e "${BORG_ENCRYPTION}" \
        "${BORG_BACKUP_PATH}/${config}" >/dev/null 2>&1
}

wrap_up() {
    for config in "${!snapper_mounted[@]}"; do
        local num="${snapper_mounted[$config]}"
        mount_snapshot "$config" umount "$num"
    done
}

# Resolve LVs into a list of descendant snapshots
for device in "${snapper_devices[@]}"; do
    # This outputs a list of snapshots into LVM2_LV_DESCENDANTS
    eval "$( lvs --noheadings --nameprefixes -o lv_descendants "$device" )"
    # shellcheck disable=2140
    eval snapper_lv_snapshots["${device##*/}"]="\$( echo \"${LVM2_LV_DESCENDANTS}\" | tr ',' '\n' )"
done

for config in "${snapper_configs[@]}"; do
    snapshot_num=$(get_latest "$config")
    if ( mount_snapshot "$config" mount "$snapshot_num" ); then
        snapshot_mount=$(
            mount | awk -v config="$config" -v num="$snapshot_num" \
                '$1 ~ config".*snapshot"num { print $3 }'
        )
        snapper_mounted[$config]="$snapshot_num"
        if [[ ! -d "${BORG_BACKUP_PATH}/$config" ]]; then
            borg_create_repo "$config" "$snapshot_num" "$snapshot_mount" || \
                { echo "Creating the repo failed"; exit 1; }
        fi
        borg_create_snap "$config" "$snapshot_num" "$snapshot_mount"
    else
        echo "Unable to mount snapshot"; exit 1
    fi
done

trap wrap_up EXIT TERM
