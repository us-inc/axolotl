### Installation From Source

sudo apt update && sudo apt -y install screen && pip install --upgrade pip setuptools wheel && pip3 install torch torchvision torchaudio && pip3 install packaging ninja && git clone https://github.com/us-inc/axolotl.git && cd axolotl && git checkout dev && pip3 install --no-build-isolation -e '.[flash-attn,deepspeed]'

### Git pull

git pull

### Environment Variable Setup

<!-- export NCCL_SOCKET_IFNAME=eth0 -->
export NCCL_SOCKET_IFNAME="eth0,en,eth,em,bond"
export GPUS_PER_NODE=8
export NNODES=7
export MASTER_ADDR=pytorch-job-465-master-0
export MASTER_PORT=30000
export NCCL_DEBUG=INFO
export NCCL_IB_DISABLE=0
export NCCL_BUFFSIZE=2097152

export WANDB_API_KEY="0b01a182246af40350de8a12ba31d0812b7e762a"

### NCCL SLURM Command

ibstat | grep -B16 InfiniBand | grep ^CA | sed "s/^CA *//1" | tr -d "'" | paste -sd,

### Screen

screen -L -Logfile output.log -S train

screen -d -r screen_name

### Wandb login

wandb login 0b01a182246af40350de8a12ba31d0812b7e762a


### Start Training Command (From shared folder)

torchrun --nnodes 8 --nproc_per_node 8 --rdzv_id "abc123" --rdzv_backend c10d --rdzv_endpoint "slurm-469-slurmd-0:30000" -m axolotl.cli.train /shared/axolotl/examples/5techlab/qwen_train_14b.yaml

### Start Training Command (From local)

torchrun --nnodes 8 --nproc_per_node 8 --rdzv_id "abc123" --rdzv_backend c10d --rdzv_endpoint "pytorch-job-471-master-0:30000" -m axolotl.cli.train examples/5techlab/qwen_train_32b.yaml

