from rbx import create_socket, spoof_request
from config import *
import threading
import random
import requests
import json
import multiprocessing
import socket

def get_cookies(resp):
    cookies = {}
    for key, values in resp.headers.items():
        if key.lower() == "set-cookie":
            values = [values] if isinstance(values, str) else values
            for value in values:
                key, value = value.split(";", 1)[0].split("=", 1)
                cookies[key] = value
    return cookies

def thread_func():
    conn = None
    while True:
        if not conn:
            try:
                conn = create_socket()
            except:
                conn = None
                continue
        ip_addr = ".".join(str(random.randint(1, 255)) for _ in range(4))
        headers = {}
        headers.update({
            "User-Agent": random.choice(user_agents),
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://www.roblox.com",
            "Referer": "https://www.roblox.com/"
        })

        try:
            try:
                headers["X-CSRF-TOKEN"] = spoof_request(conn, "POST", "https://auth.roblox.com/v2/signup", ip=ip_addr, headers=headers, data="{}").headers["x-csrf-token"]
            except:
                continue
 
            username, password, birthday, gender = generate_details()
            payload = json.dumps({
                "username": username,
                "password": password,
                "birthday": birthday,
                "gender": gender,
                "isTosAgreementBoxChecked": True,
                "context": "MultiverseSignupForm",
                "referralData": None,
                "displayAvatarV2": False,
                "displayContextV2": False
            }, separators=(",", ":"))
            resp = spoof_request(
                conn,
                "POST",
                "https://auth.roblox.com/v2/signup",
                headers=headers,
                data=payload,
                ip=ip_addr
            )
            
            if resp.text.startswith('{"userId":'):
                data = resp.json()
                cookies = get_cookies(resp)
                print(f"[CREATED ACCOUNT] Id:{data['userId']}, Name:{username}")

                with open("cookies.txt", "a", encoding="UTF-8", errors="ignore") as fp:
                    fp.write(cookies[".ROBLOSECURITY"] + "\n")
                    
                with open("full.txt", "a", encoding="UTF-8", errors="ignore") as fp:
                    fp.write("||".join([
                        str(data["userId"]),
                        username,
                        password,
                        birthday,
                        str(gender),
                        ";;".join(f"{k}={v}" for k,v in cookies.items()),
                        ip_addr,
                        headers["User-Agent"]
                    ]))
        except Exception as err:
            print(err)

        finally:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()
            conn = None

def worker():
    for _ in range(THREAD_COUNT):
        threading.Thread(target=thread_func).start()

if __name__ == "__main__":
    for _ in range(WORKER_COUNT):
        multiprocessing.Process(target=worker).start()