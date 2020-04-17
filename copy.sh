nodes=(0 22 23 24 25)
for node in "${nodes[@]}"
do
    ssh cc-$node "pip uninstall -y sshmpi && pip install git+git://github.com/brendanxwhitaker/sshmpi.git && rm ~/spout"
done


#for node in "${nodes[@]}"
#do
#    ssh cc-$node "rm -rf ~/pkgs/sshmpi && cd ~/pkgs/ && git clone https://github.com/brendanxwhitaker/sshmpi.git && pip install -r ~/pkgs/sshmpi/requirements.txt"
#done
#
#for node in "${nodes[@]}"
#do
#    ssh cc-$node "cp ~/pkgs/sshmpi/sshmpi/spout.py ~/spout && chmod +x ~/spout"
#done
