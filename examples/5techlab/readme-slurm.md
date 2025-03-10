parallel-ssh -H <> sudo apt update && sudo apt -y install screen && pip install --upgrade pip setuptools wheel && pip3 install torch torchvision torchaudio && pip3 install packaging ninja && git clone https://github.com/us-inc/axolotl.git && cd axolotl && git checkout dev && pip3 install --no-build-isolation -e '.[flash-attn,deepspeed]'

for i in slurm-473-slurmd-{0..15}; do echo ssh $i 'bash /shared/node-test.sh'; done | tee node-test-128xh100-20250310.log

for i in slurm-473-slurmd-{0..15}; do ssh $i 'service slurmd restart'; done

for i in slurm-473-slurmd-{0..1}; do ssh $i 'service slurmd restart'; done
for i in slurm-473-slurmd-{0..1}; do ssh $i 'sudo service slurmd restart'; done

for i in slurm-473-slurmd-{2..15}; do ssh $i 'sudo service slurmd restart'; done

for i in slurm-473-slurmd-{0..15}; do ssh $i 'sudo service slurmd restart'; done

OMPI_MCA_coll=^hcoll
