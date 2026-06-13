from fastapi import FastAPI, Body
from src.ensemble import EnsembleEngine
from src.config_handler import load_config, save_config

app = FastAPI(title="Banking Threat Detection API")
engine = EnsembleEngine()

@app.get("/")
def read_root():
    return {"message": "Banking Threat Detection API is running"}

@app.post("/score/transaction")
def score_transaction(data: dict = Body(...)):
    res = engine.providers["transaction"].score(data)
    return res

@app.post("/score/network")
def score_network(data: dict = Body(...)):
    res = engine.providers["network"].score(data)
    return res

@app.post("/score/device")
def score_device(data: dict = Body(...)):
    res = engine.providers["device"].score(data)
    return res

@app.post("/score/context")
def score_context(data: dict = Body(...)):
    res = engine.providers["context"].score(data)
    return res

@app.post("/score/final")
def score_final(data: dict = Body(...)):
    res = engine.evaluate(data)
    return res

@app.get("/config")
def get_config():
    return load_config()

@app.post("/config")
def update_config(new_config: dict = Body(...)):
    save_config(new_config)
    # Reload engine with new config
    global engine
    engine = EnsembleEngine()
    return {"message": "Configuration updated successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
