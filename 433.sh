python -m vllm.entrypoints.openai.api_server \
   --model 1:\
   --tensor-parallel-size 4 \
   --gpu-memory-utilization=0.95 \
   --max-num-seqs 16 \
   --port 8080 \
   --enforce-eager \
   --trust-remote-code 
