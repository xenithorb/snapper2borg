#!/bin/bash

BORG_BACKUP_PATH="/mnt/external1/backups"
BORG_COMPRESSION="auto,zstd"
BORG_FLAGS="-x -s"
#BORG_FLAGS="-x -s -p"
#BORG_PASSPHRASE="${BORG_PASSPHRASE}"
BORG_PRUNE_FLAGS="--keep-witin 1d -d 10 -w 10 -m 6"
BORG_PASSCOMMAND="cat /root/.borg_password"
BORG_ENCRYPTION="repokey-blake2"
BIND_MNT_PREFIX="/tmp/borg"

export BORG_PASSPHRASE BORG_PASSCOMMAND
declare -A snapper_lv_snapshots snapper_mounted

check_root() {
    # Check for root
    (( EUID == 0 )) || { echo "This script must be run as root"; exit 1; }
}

mutex() {
    # MUTEX Do not remove
    lockdir="${BORG_BACKUP_PATH}/.snapper2borg.lock"
    if ! mkdir "$lockdir" >/dev/null 2>&1; then
        echo "${0##*/} cannot run more than once, or remove the lockdir at: $lockdir"
        exit 1
    fi
}

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
    borg init \
        -e "${BORG_ENCRYPTION}" \
        "${BORG_BACKUP_PATH}/${config}" >/dev/null 2>&1
}

borg_prune_repo() {
    local config="$1"
    # shellcheck disable=2086
    borg prune -a "*-snapshot*" ${BORG_PRUNE_FLAGS} \
    "${BORG_BACKUP_PATH}/${config}"
}

borg_get_names() {
    # Outputs a list of archives in borg
    local config="$1"
    borg list -a "*-snapshot*" "${BORG_BACKUP_PATH}/${config}" \
        --format '{name}{NL}'
}

bind_mount_snapshot() {
    # Returns the bind mountpoint of the snapshot
    local bind_path="${BIND_MNT_PREFIX}/$1"
    local snapshot="$2"
    mkdir -p "${BIND_MNT_PREFIX}" &&
    mount -o bind,x-mount.mkdir=0600 "$snapshot" "$bind_path"
    return=$?; (( return == 0 )) && echo "$bind_path"
    return $return
}

wrap_up() {
    for config in "${!snapper_mounted[@]}"; do
        local num="${snapper_mounted[$config]}"
        mount_snapshot "$config" umount "$num"
    done
    # for mountpoint in "${bind_mount_paths[@]}"; do
    #     umount -l "$mountpoint"
    # done
    umount -l "${bind_mount_paths[@]}"
    rmdir "$lockdir"
}

trap wrap_up INT EXIT TERM
error=0

check_root
mutex

# Get configured snapper filesystems
snapper_filesystems=($( snapper list-configs | awk 'NR > 2 { print $3 }' ))
snapper_configs=($( snapper list-configs | awk 'NR>2 { print $1 }' ))
snapper_devices=($(
    for mount in "${snapper_filesystems[@]}"; do
        __df_output=($( df -l --no-sync --output=source "$mount" ))
        echo "${__df_output[1]}"
    done
))

# Resolve LVs into a list of descendant snapshots
for device in "${snapper_devices[@]}"; do
    # This outputs a list of snapshots into LVM2_LV_DESCENDANTS
    eval "$( lvs --noheadings --nameprefixes -o lv_descendants "$device" )"
    # shellcheck disable=2140
    eval snapper_lv_snapshots["${device##*/}"]="\$( echo \"${LVM2_LV_DESCENDANTS}\" | tr ',' '\n' )"
done

for i in "${!snapper_configs[@]}"; do
    config="${snapper_configs[i]}"
    device="${snapper_devices[i]}"
    snapshot_num=$(get_latest "$config")

    if [[ "$SYSTEMD_INSTANCE" =~ (snapper-timeline|^$) ]] &&
        ( mount_snapshot "$config" mount "$snapshot_num" ); then
        snapper_mounted[$config]="$snapshot_num"
        snapshot_mount=$(
            mount | awk \
                -v device="$device" \
                -v num="$snapshot_num" \
                -v bind_pre="$BIND_MNT_PREFIX" \
                '$1 ~ device"--snapshot"num && $3 !~ bind_pre { print $3 }'
        )
        bind_mount_paths+=($( bind_mount_snapshot "${device##*/}" "$snapshot_mount" )) ||
            { echo "Could not bind mount the snapshot"; error=1; continue; }
        if [[ ! -d "${BORG_BACKUP_PATH}/$config" ]]; then
            borg_create_repo "$config" ||
                { echo "Borg - Creating the repo failed"; error=1; continue; }
        fi
        borg_create_snap "$config" "$snapshot_num" "${bind_mount_paths[-1]}" ||
            { echo "Borg - Archive error, not created properly"; error=1; continue; }
    else
        echo "Unable to mount snapshot"; error=1; continue
    fi

    if [[ "$SYSTEMD_INSTANCE" == "snapper-cleanup" ]]; then
        borg_prune_repo "$config" ||
            { echo "Borg - Repository prune error"; error=1; continue; }
    fi
done

exit $error
