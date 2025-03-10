#!/bin/bash

set -e
set -u
set -o pipefail

# Globals
IF_NAME="eth0"

usage() {
    echo "Usage: $0 [--single] [HOSTNAME_OR_IP...]"
    echo
    echo "Options:"
    echo "  --single  Run single node test. Optional, if no hosts are given, it is assumed."
    echo
    echo "Arguments:"
    echo "  One or more hostnames or IP addresses. Optional"
    echo
    echo "Examples:"
    echo "# Only test the local host:"
    echo "  $0"
    echo "# Test connectivity between localhost and 10.0.0.2:"
    echo "  $0 10.0.0.2"
    echo "# Test localhost and then test connectivity between the three nodes:"
    echo "  $0 --single server1.example.com 192.168.1.1"
   exit 1
}

SINGLE="no"
HOSTS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
	--help|-h)
	    usage
	    ;;
	--single)
	    SINGLE="yes"
	    shift
	    ;;
	*)
	    HOSTS+=("$1")
	    shift
	    ;;
    esac
done

if [[ ${#HOSTS[@]} -eq 0 && $SINGLE == "no" ]]; then
    SINGLE="yes"
fi

echo "SINGLE: $SINGLE"
echo "HOSTS: ${HOSTS[*]}"

error_exit() {
    echo "ERROR: $1" >&2
    exit 1
}

get_infiniband_hca() {
    ibstat | grep -B16 InfiniBand | grep ^CA | sed "s/^CA *//1" | tr -d "'"
}

get_infiniband_devinfo() {
    ibv_devinfo | sed -n -e '/hca_id/p' -e '/link_layer:/p' | grep -B1 InfiniBand | grep hca_id | sed -e 's/^hca_id://g' | tr -d '[[:blank:]]'
}

check_infiniband() {
    readonly EXPECTED_STATUS="Active"
    readonly EXPECTED_PHYS_STATUS="LinkUp"
    readonly EXPECTED_LINK_LAYER="InfiniBand"
    readonly EXPECTED_RATE=400

    IB_STAT="$(get_infiniband_hca | sort | paste -sd,)"
    IB_DEVINFO="$(get_infiniband_devinfo | sort | paste -sd,)"
    echo "$IB_STAT (ibstat)"
    echo "$IB_DEVINFO (ibv_devinfo)"
    [[ "$IB_STAT" != "$IB_DEVINFO" ]] && echo "WARNING: ibstat and ibv_devinfo InfiniBand devices do not match" #XXX

    HCA="$(get_infiniband_hca)"
    for i in $HCA; do
	echo -n "$i"
	IBSTAT=$(ibstat $i)
	STATUS=$(echo "$IBSTAT" | grep State: | cut -d: -f2 | tr -d ' ')
	echo -n " | $STATUS"
	PHYS_STATUS=$(echo "$IBSTAT" | grep 'Physical state:' | cut -d: -f2 | tr -d ' ')
	echo -n " | $PHYS_STATUS"
	LINK_LAYER=$(echo "$IBSTAT" | grep 'Link layer:' | cut -d: -f2 | tr -d ' ')
	echo -n " | $LINK_LAYER"
	RATE=$(echo "$IBSTAT" | grep 'Rate:' | cut -d: -f2 | tr -d ' ')
	echo -n " | $RATE"
	echo

	[[ $STATUS != "$EXPECTED_STATUS" ]] && error_exit "Status is not $EXPECTED_STATUS got $STATUS"
	[[ $PHYS_STATUS != "$EXPECTED_PHYS_STATUS" ]] && error_exit "Physical state is not $EXPECTED_PHYS_STATUS got $PHYS_STATUS"
	[[ $LINK_LAYER != "$EXPECTED_LINK_LAYER" ]] && error_exit "Link layer is not $EXPECTED_LINK_LAYER got $LINK_LAYER"
	[[ $RATE -ne $EXPECTED_RATE ]] && error_exit "Rate is not $EXPECTED_RATE, got $RATE"
    done
    return 0
}

check_infiniband_multinode() {
    SECONDARY_NODE_IP=$1
    echo "START Check InfiniBand ports on $SECONDARY_NODE_IP"
    ssh $SECONDARY_NODE_IP \
	"$(declare -f check_infiniband); \
	$(declare -f get_infiniband_hca); \
	$(declare -f get_infiniband_devinfo); \
	$(declare -f error_exit); 	      \
       check_infiniband" || error_exit "InfiniBand ports check failed for $SECONDARY_NODE_IP"

    REMOTE_HCA=$(ssh $SECONDARY_NODE_IP \
	"$(declare -f check_infiniband); \
	$(declare -f get_infiniband_hca); \
	$(declare -f get_infiniband_devinfo); \
	$(declare -f error_exit); \
        get_infiniband_hca" | sort | paste -sd,)

    LOCAL_HCA="$(get_infiniband_hca | sort | paste -sd,)"
    if [[ "$LOCAL_HCA" != "$REMOTE_HCA" ]]; then
	echo "WARNING: InfiniBand port names differ on localhost and $SECONDARY_NODE_IP"
    fi
    echo "END Check InfiniBand ports on $SECONDARY_NODE_IP"

    echo "START Check multi-port bandwidth test between localhost and $SECONDARY_NODE_IP"
    MASTER_IP=$(ifconfig $IF_NAME | awk '/inet / { print $2 }')
    echo "run_perftest_multi_devices
	-d `echo \"$LOCAL_HCA\" | paste -sd,`
	-c `echo {0..7} | sed 's/ /,/g'`
	--cmd 'ib_write_bw --report_gbits -a'"
    run_perftest_multi_devices \
	-d `echo "$LOCAL_HCA" | paste -sd, ` \
	-c `echo {0..7} | sed 's/ /,/g' `  \
	--cmd "ib_write_bw --report_gbits -a" &
    PID_BG=$!
    sleep 5
    ps -p $PID_BG 1>/dev/null || error_exit "Failed to create server process"
    CMD="run_perftest_multi_devices \
    	-d `echo \"$REMOTE_HCA\" | paste -sd,` \
	-c `echo {0..7} | sed 's/ /,/g' `  \
	-r $MASTER_IP \
	--cmd 'ib_write_bw --report_gbits -a'"
    echo "($SECONDARY_NODE_IP) \$ $CMD"
    ssh $SECONDARY_NODE_IP "$CMD"
    FG_RES=$?
    wait
    if [[ $FG_RES -ne 0 ]]; then
        echo "WARNING: Client exited with non-zero status: ${FG_RES}, manually killing processes, if any"
        pgrep -a ib_write_bw && (killall -v ib_write_bw || echo "Error: Failed to kill ib_write_bw processes on the master node")
        ssh $SECONDARY_NODE_IP \
            "pgrep -a ib_write_bw && (killall -v ib_write_bw || echo 'Failed to kill ib_write_bw processes on the secondary node')"
    fi
    echo "END Check multi-port bandwidth test between localhost and $SECONDARY_NODE_IP"
    return 0
}

check_limits() {
    readonly EXPECTED_ULIMIT_M="unlimited"   # max memory
    ## readonly EXPECTED_ULIMIT_L="unlimited" # max locked memory
    readonly EXPECTED_ULIMIT_L=90000000 # max locked memory
    readonly EXPECTED_ULIMIT_N=1000000 # max opened files

    ULIMIT_M=$(ulimit -m)
    ULIMIT_L=$(ulimit -l)
    ULIMIT_N=$(ulimit -n)

    [[ "$ULIMIT_M" != "$EXPECTED_ULIMIT_M" ]] && error_exit "ulimit -m is not $EXPECTED_ULIMIT_M, got $ULIMIT_M"
    [[ "$ULIMIT_L" -lt "$EXPECTED_ULIMIT_L" ]] && error_exit "ulimit -l is not $EXPECTED_ULIMIT_L, got $ULIMIT_L"
    [[ "$ULIMIT_N" -lt "$EXPECTED_ULIMIT_N" ]] && error_exit "ulimit -n is not $EXPECTED_ULIMIT_N, got $ULIMIT_N"
    return 0
}

check_gpu_bw_single_node() {
    readonly GPU_TX_SIZE="1G"
    readonly EXPECTED_NCCL_BW=400

    NCCL_OUT=$(NCCL_DEBUG=INFO /opt/nccl-tests/build/all_reduce_perf  -b $GPU_TX_SIZE -e $GPU_TX_SIZE -f2 -g8 | tee /dev/tty)
    NCCL_BW=$(echo "$NCCL_OUT" | grep 'Avg bus bandwidth' | cut -d: -f 2 | tr -d ' ')
    [[ "${NCCL_BW%%.*}" -lt "$EXPECTED_NCCL_BW" ]] && error_exit "NCCL_BW is less than $EXPECTED_NCCL_BW, got $NCCL_BW"
    return 0
}

echo "START Check InfiniBand ports on localhost"
check_infiniband || error_exit "InfiniBand test failed"
echo "END InfiniBand port test on localhost"

if [[ $SINGLE == "yes" ]]; then
    echo "START Check file and memory limits on localhost"
    check_limits || error_exit "ulimit check failed"
    echo "END Check file and memory limits on localhost"

    NCCL_SOCKET_IFNAME=$IF_NAME
    echo "START Single node GPU bandwidth test"
    NCCL_IB_HCA="$(get_infiniband_hca | paste -sd,)"
    echo "NCCL_IB_HCA: $NCCL_IB_HCA"
    # export UCX_NET_DEVICES="$(get_infiniband_hca | sed 's/$/:1/g' | paste -sd,)"
    # echo "export UCX_NET_DEVICES: $UCX_NET_DEVICES"
    echo "NCCL_SOCKET_IFNAME: $NCCL_SOCKET_IFNAME"
    check_gpu_bw_single_node || error_exit "Single node GPU bandwidth test failed"
    echo "END Single node GPU bandwidth test"
fi

if [[ ${#HOSTS[@]} -ne 0 ]]; then
    for NODE in ${HOSTS[*]}; do
        echo "START Check file and memory limits on $NODE"
        ssh $NODE \
            "$(declare -f check_limits); \
	$(declare -f error_exit);    \
        check_limits" || error_exit "ulimit check failed for $NODE"
        echo "END Check file and memory limits on $NODE"

        echo "START Multi-node InfiniBand bandwidth test"
        check_infiniband_multinode "$NODE" || error_exit "FAILED Multi-node InfiniBand bandwidth test"
    done

    HFILE=$(mktemp)
    MASTER_IP=$(ifconfig $IF_NAME | awk '/inet / { print $2 }')
    echo "START Multi-node GPU bandwidth test"
    echo "${MASTER_IP} slots=8" | tee $HFILE
    for NODE in ${HOSTS[*]}; do
        echo "$(ssh $NODE hostname -i) slots=8" | tee -a $HFILE
    done
    NP=$(( $(( ${#HOSTS[@]} + 1 )) * 8 ))

    NCCL_SOCKET_IFNAME=eth0
         ## -x UCX_NET_DEVICES="$UCX_NET_DEVICES" \
         ## -x UCX_TLS=tcp \
         ##  -x UCX_NET_DEVICES=eth0 \
         ## -x OMPI_MCA_btl_tcp_if_include=eth0 \
         ##  -x OMPI_MCA_btl=tcp,self \
         ## -mca coll ^hcoll \
         # -x NCCL_IB_HCA="$NCCL_IB_HCA" \
    mpirun \
       --allow-run-as-root \
       --bind-to numa \
       -np $NP \
       --hostfile $HFILE \
       -x OMPI_MCA_coll=^hcoll \
       -x UCX_LOG_LEVEL=INFO \
       -x NCCL_DEBUG=INFO \
       -x NCCL_SOCKET_IFNAME="$NCCL_SOCKET_IFNAME" \
       /opt/nccl-tests/build/all_reduce_perf -b 1G -e 16G -f2 -g1 || (rm -vf $HFILE ; error_exit "FAILED Multi-node GPU bandwidth test")
    echo "END Multi-node GPU bandwidth test"
fi

# TODO: Test NIC firmware version

exit 0
