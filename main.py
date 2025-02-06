from fastapi import FastAPI, Request, HTTPException, Depends, Form
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
import sqlite3
import random
from uuid import uuid4

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DATABASE_URL = "./local.db" 

def init_db():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Teams (
            name TEXT PRIMARY KEY
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS UUIDs (
            id TEXT PRIMARY KEY
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS WordMappings (
            id TEXT,
            team_name TEXT,
            word TEXT,
            FOREIGN KEY (team_name) REFERENCES Teams (name)
        )
    ''')

    for _ in range(12):
        cursor.execute("INSERT INTO UUIDs (id) VALUES (?)", (str(uuid4()),))

    conn.commit()
    conn.close()

init_db()

words = [f'word {i}' for i in range(50)]

def team_exists(team_name: str) -> bool:
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM Teams WHERE LOWER(name) = ?", (team_name.lower(),))
    team = cursor.fetchone()
    conn.close()
    return team is not None

##########################################################################################

@app.get("/")
async def index(req: Request):
    return templates.TemplateResponse("index.html", {"request": req})

@app.post("/register")
async def register(team_name: str = Form(...)):
    if not team_name:
        raise HTTPException(status_code=400, detail="Team name is required")
    
    if team_name.strip() == "":
        raise HTTPException(status_code=400, detail="Team name cannot be empty")
    
    if team_exists(team_name):
        raise HTTPException(status_code=400, detail="Team name already registered")

    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO Teams (name) VALUES (?)''', (team_name,))
    conn.commit()
    conn.close()

    return None, 201


@app.get("/get-word/{id}")
async def get_word(req: Request, id: str):
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM UUIDs WHERE id = ?", (id,))
    uuid = cursor.fetchone()

    if not uuid:
        return templates.TemplateResponse("cheating.html", {"request": req})

    return templates.TemplateResponse("get-word.html", {"request": req, "id": id})


@app.post("/get-word/{id}")
async def get_word(id: str, team_name: str = Form(...)):
    if not team_exists(team_name):
        raise HTTPException(status_code=400, detail="Team name is not registered!!")
    
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("SELECT word FROM WordMappings WHERE id = ? AND team_name = ?", (id, team_name))
    word = cursor.fetchone()

    if word is not None:
        conn.close()
        return {"word": word[0]}
    
    wordIdx = random.randint(0, len(words) - 1)
    word = words.pop(wordIdx)
    
    cursor.execute("INSERT INTO WordMappings (id, team_name, word) VALUES (?, ?, ?)", (id, team_name, word))
    conn.commit()
    conn.close()

    return {"word": word}


@app.get("/admin-mai-tera-baap-hu")
def admin(req: Request):
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("SELECT team_name, GROUP_CONCAT(word) FROM WordMappings GROUP BY team_name")
    mappings = cursor.fetchall()

    conn.close()

    team_data = {team_name: words.split(',') for team_name, words in mappings}
    return templates.TemplateResponse("admin.html", {"request": req, "team_data": team_data})