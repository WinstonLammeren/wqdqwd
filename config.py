import random
import requests

THREAD_COUNT = 50
WORKER_COUNT = 64

words = requests.get("https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt").text.splitlines()
user_agents = requests.get("https://jnrbsn.github.io/user-agents/user-agents.json").json()
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def generate_details():
    username = "".join(random.choices(words, k=3))[:20]
    password = "".join(random.choices(words, k=3))[:20]
    birthday = f"{random.randint(1, 28):02d} {random.choice(months)} {random.randint(1991, 2006)}"
    gender = 2
    return (username, password, birthday, gender)