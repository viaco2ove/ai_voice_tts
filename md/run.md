windows
```bash
cd D:\Users\viaco\PycharmProjects\CosyVoice
.venv\Scripts\activate
python.exe api.py
```

or
```bash
cd /mnt/d/Users/viaco/tools/voice                                                                                                               
source .venv/bin/activate                                                                                                                       
export PYTHONPATH=$PWD                                                                                                                          
VOICE_CONFIG_PATH=config/services.yaml uvicorn src.voice_service.main:app --host 0.0.0.0 --port 8000  
```

or

windows
```bash
cd D:\Users\viaco\PycharmProjects\CosyVoice
./scripts/start_all.sh
```
or

```bash
bash --noprofile --norc -c 'cd /mnt/d/users/viaco/tools/voice && source .venv/bin/activate && python -m src.voice_service.launcher --config config/services.yaml'  
```     

```bash
cd /mnt/d/Users/viaco/tools/voice                                                                                                               
source .venv/bin/activate    
pip install -r requirements.txt
```

```bash                                                                                                        
export PYTHONPATH=$PWD                                                                                                                          
VOICE_CONFIG_PATH=config/services.yaml uvicorn src.voice_service.main:app --host 0.0.0.0 --port 8000  
```