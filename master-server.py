import os
import a2s
import requests
import json
import time
import socket
from colorama import Fore
import sys
import signal

#import logging
#import sys

#root = logging.getLogger()
#root.setLevel(logging.DEBUG)

#handler = logging.StreamHandler(sys.stdout)
#handler.setLevel(logging.DEBUG)
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#handler.setFormatter(formatter)
#root.addHandler(handler)

#from discord_webhook import DiscordWebhook, DiscordEmbed

#try:
#    config = json.load(open("config.json", 'r'))
#    webhook = config["webhook"]
#except Exception as e:
#    print(f"Failed to load config and grab Discord URL: {e}")

#webhook = DiscordWebhook(url={}.format(webhook))
#
## create embed object for webhook
## you can set the color as a decimal (color=242424) or hex (color='03b2f8') number
#embed = DiscordEmbed(title='Python Master Server', description='{}', color='00ffbf')
#embed.add_embed_field(name='{}', value='{}')
#webhook.add_embed(embed)
#response = webhook.execute()

# Creators.TF Master Server
# Written by ZoNiCaL.
# edited by sapphonie
# Purpose: Updates the Creators.TF database with the latest website information.

# Custom exception class to diagnose problems that specifically happen with the
# Creators.TF API. This could help diagnose problems later if needed.
# ^^^ ??? what??
class CreatorsTFAPIError(BaseException):
    pass


masterKey = ""
try:
    configFile = json.load(open("config.json", 'r'))
except Exception as e:
    pass
def GetConfigValue(key, default):
    if key in configFile.keys():
        if key is not "":
            return configFile[key]
    return os.getenv(key, default)

def GetConfigValueList(key, default):
    value = GetConfigValue(key, default)
    if isinstance(value, list):
        return value
    return value.split(',')

class config():
    SLEEPTIME = GetConfigValue("sleeptime", 10)
    # Master API key. This allows the website to
    # recognise us when we make requests.
    MASTERKEY = GetConfigValue("masterKey", GetConfigValue("key", None))
    # Currently, we only care about a few providers in our network, that being
    # Creators.TF, Balance Mod, Silly Events servers, and Creators.TF Vanilla+.
    # For now, we don't have a way to grab providers dynamically
    PROVIDERS = GetConfigValue("providers", [ 15, 1756, 11919, 78132 ])

if config.MASTERKEY is None:
    print(f"Failed to load config and grab API key")
    quit()


isRunning = True

def signal_handler(sig, frame):
    global isRunning
    print('You pressed Ctrl+C!')
    print('stoping when done')
    isRunning = False

signal.signal(signal.SIGINT, signal_handler)

while isRunning:
    # Grab our server list with an HTTP request.
    for provider in config.PROVIDERS:
        requestURL = f"https://creators.tf/api/IServers/GServerList?provider={provider}"
        # Make an API request to the website.
        try:
            req = requests.get(requestURL, timeout=5)    # Return a JSON object which we can iterate over.
            serverList = req.json()

            #print(f"{serverList}")

            # If the API returned something that wasn't a SUCCESS, something wen't wrong
            # on the website-end, so we'll just skip this provider for now.
            if serverList["result"] != "SUCCESS":
                raise CreatorsTFAPIError(f"[{req.status_code}] API (GServerList) returned non-SUCCESS code.")

        # If we run into some sort of error making a request, we'll just skip this provider.
        except BaseException as e:
            print(f"[FAIL] Request failed for provider {provider}: {e}")
            continue

        serversToSend = []

        # Loop through all the returned servers and request information for them.
        for server in serverList["servers"]:
            print(server["ip"], server["port"])
            serverstr = str(server['ip']) + ":" + str(server['port'])
            try:
                serverID = server["id"]
                timeout = 3.0
                a2sInfoRequest = a2s.info((server["ip"], server["port"]), timeout)

                # Construct a JSON object with all of our server information.
                info = {
                    "hostname":         a2sInfoRequest.server_name,
                    "online":           a2sInfoRequest.player_count,
                    "maxplayers":       a2sInfoRequest.max_players,
                    "map":              a2sInfoRequest.map_name,
                    #"keywords":         a2sInfoRequest.keywords,
                    #"bots":             a2sInfoRequest.bot_count,
                    #"game":             a2sInfoRequest.game,
                    #"appid":            a2sInfoRequest.app_id,
                    #"version":          a2sInfoRequest.version,
                    #"passworded":       a2sInfoRequest.password_protected,
                    #"vac_secure":       a2sInfoRequest.vac_enabled,
                    #"sourcetv_port":    a2sInfoRequest.stv_port,
                    #"sourcetv_name":    a2sInfoRequest.stv_name,
                }

                # This could totally have more support for more data later like
                # actual players. If we consider doing a "recent activity" feature,
                # we could return other player info.

                #Construct an object that we'll send to the database soon:
                serverToSend = {
                    "id": serverID,
                    "datapack": info
                }

                # Add to our final list:
                serversToSend.append(serverToSend)

                print(Fore.GREEN + f"[SUCCESS] {serverstr}: {a2sInfoRequest.server_name}, {a2sInfoRequest.player_count}/{a2sInfoRequest.max_players}" + Fore.RESET)

            #except BrokenMessageError:
            #    print("a")
            except socket.timeout:
                print(Fore.RED + f"[TIMEOUT] {serverstr}" + Fore.RESET)
            except ConnectionRefusedError:
                print(Fore.RED + f"[REFUSED] {serverstr}" + Fore.RESET)
            except socket.gaierror:
                print(Fore.RED + f"[NOSERVER] {serverstr}" + Fore.RESET)
            except OSError:
                print(Fore.RED + f"[OSERROR] {serverstr}" + Fore.RESET)

        # We've now got a list of servers for this provider. Create a request to the
        # website API that updates server information in the database.
        requestURL = f"https://creators.tf/api/IServers/GHeartbeat"
        # Make an API request to the website.
        try:
            req = requests.post(requestURL,
                data={ "servers": serversToSend, "key": masterKey })
            resp = req.json()   # Return a JSON object which we can iterate over.

            # If the API returned something that wasn't a SUCCESS, something wen't wrong
            # on the website-end, so we'll just skip this provider for now.
            if resp["result"] != "SUCCESS":
                raise CreatorsTFAPIError(f"[{req.status_code}] API (GHeartbeat) returned non-SUCCESS code.")

            print(f"Successfully updated provider {provider}")
        except BaseException as e:
            print(e)
            continue

    # stupid bad code awful dogshit don't do this
    seconds = ""
    if config.SLEEPTIME != 1:
        seconds = "s"

    print(Fore.MAGENTA + f"Sleeping for {int(config.SLEEPTIME)} second{seconds}..."  + Fore.RESET)
    time.sleep(int(config.SLEEPTIME))

if isRunning is False:
    os._exit(1)
