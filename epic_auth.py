import aiohttp
import requests
import asyncio
import os
import platform
import json
import math
from typing import Optional
from datetime import datetime, timezone
from cosmetic import FortniteCosmetic
from utils import bool_to_emoji

# these tokens are used to authorize in epic games's API and let us do the skincheck without getting errors
EPIC_API_SWITCH_TOKEN = "OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3"
# keep in mind, sometimes epic games block the client ids, so then you have to generate new ios token for it to start working again
EPIC_API_IOS_CLIENT_TOKEN = "M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU="

class EpicEndpoints:
    endpoint_oauth_token = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"
    endpoint_prod03_oauth_token = "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token"
    endpoint_redirect_url = "https://www.epicgames.com/id/login?redirectUrl=https%3A//www.epicgames.com/id/login%3FredirectUrl%3Dhttps%253A%252F%252Fwww.epicgames.com%252Fid%252Fapi%252Fredirect%253FclientId%253Dec684b8c687f479fadea3cb2ad83f5c6%2526responseType%253Dcode"
    endpoint_oauth_exchange = "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/exchange"
    endpoint_device_auth = "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/deviceAuthorization"

# locker categories we render
locker_categories = ['AthenaCharacter', 'AthenaBackpack', 'AthenaPickaxe', 'AthenaDance', 'AthenaGlider', 'AthenaPopular', 'AthenaExclusive']

class EpicUser:
    def __init__(self, data: dict = {}):
        self.raw = data

        # api response for login link generation
        self.access_token = data.get("access_token", "")
        self.expires_in = data.get("expires_in", 0)
        self.expires_at = data.get("expires_at", "")
        self.token_type = data.get("token_type", "")
        self.client_id = data.get("client_id", "")
        self.internal_client = data.get("internal_client", False)
        self.client_service = data.get("client_service", "")
        self.product_id = data.get("product_id", "")
        self.application_id = data.get("application_id", "")

        # api response for account metadata
        self.refresh_token = data.get("refresh_token", "")
        self.refresh_expires = data.get("refresh_expires", "")
        self.refresh_expires_at = data.get("refresh_expires_at", "")
        self.account_id = data.get("account_id", "")
        self.display_name = data.get("displayName", "")
        self.app = data.get("app", "")
        self.in_app_id = data.get("in_app_id", "")
        self.acr = data.get("acr", "")
        self.auth_time = data.get("auth_time", "")

class LockerData:
    def __init__(self):
        self.cosmetic_categories = {}
        self.cosmetic_array = {}
        self.unlocked_styles = {}
        self.homebase_banners = {}
        self.last_match = ''

    def to_dict(self):
        return {
            "cosmetic_categories": self.cosmetic_categories,
            "cosmetic_array": self.cosmetic_array,
            "unlocked_styles": self.unlocked_styles,
            "homebase_banners": self.homebase_banners,
        }

def add_missing_array2(arr, arr2, category, idclean):
    # i hate hardcoding stuff, so ill make helper funcs instead
    if category not in arr:
        arr[category] = []
        arr2[category] = []

    arr[category].append(idclean)

def add_missing_array(arr, arr2, category):
    # i hate hardcoding stuff, so ill make helper funcs instead
    if category not in arr:
        arr[category] = []
        arr2[category] = []

async def get_cosmetic_data(cosmetic_lowercase_id):
    try:
        response = requests.get(
            f'https://fortnite-api.com/v2/cosmetics/br/search/ids?language=en{cosmetic_lowercase_id}'
        )

        response.raise_for_status()
        return response.json().get('data', [])
    
    except Exception as e:
        print(f"Error getting cosmetic info for cosmetic with ID: {cosmetic_lowercase_id}\n> Exception: {e}")
        return []
    
class EpicGenerator:
    def __init__(self) -> None:
        # init the generator
        self.http: aiohttp.ClientSession
        self.user_agent = f"DeviceAuthGenerator/{platform.system()}/{platform.version()}"
        self.access_token = ""

    async def start(self) -> None:
        self.http = aiohttp.ClientSession(headers={"User-Agent": self.user_agent})
        self.access_token = await self.get_access_token()

    async def kill(self) -> None:
        await self.http.close()
    
    async def get_access_token(self) -> str:
        # getting the access token from epic's api(REQUIRES usage of EPIC_API_SWITCH_TOKEN as Authorization in headers for it to work)
        # if it's not getting any data, it means the EPIC_API_SWITCH_TOKEN is expired, you must find new one :D
        async with self.http.request(
            method="POST",
            url=EpicEndpoints.endpoint_oauth_token,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"basic {EPIC_API_SWITCH_TOKEN}"
            },
            data={ "grant_type": "client_credentials" },
        ) as response:
            data = await response.json()
            return data["access_token"]
        
    async def create_device_code(self) -> tuple:
        # devide code is used on the link the checker bot sends u "active?userCode=SOMETHING" something like this
        # REQUIRES usage of self.access_token, which we got from get_access_token function, as Authorization in headers
        # returns the device code, used in the link we generate for the user to login
        async with self.http.request(
            method="POST",
            url=EpicEndpoints.endpoint_device_auth,
            headers={
                "Authorization": f"bearer {self.access_token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        ) as response:
            data = await response.json()
            return data
        
    async def create_exchange_code(self, user: EpicUser) -> str:
        # creates exchange code for the api requests & returns it
        # REQUIRES usage of user.access_token, which we got from get_access_token function, as Authorization in headers
        async with self.http.request(
            method="GET",
            url=EpicEndpoints.endpoint_oauth_exchange,
            headers={"Authorization": f"bearer {user.access_token}"},
        ) as response:
            data = await response.json()
            return data["code"]
        
    async def wait_for_device_code_completion(self, bot, message, code: str) -> Optional[EpicUser]:
        while True:
            try:
                async with self.http.request(
                    method="POST",
                    url=EpicEndpoints.endpoint_prod03_oauth_token,
                    headers={
                        "Authorization": f"basic {EPIC_API_SWITCH_TOKEN}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"grant_type": "device_code", "device_code": code},
                    timeout=10
                ) as request:
                    token_data = await request.json()

                    if request.status == 200 and "access_token" in token_data:
                        break

                    # Handle specific API errors
                    error_code = token_data.get("errorCode")
                    if error_code == "errors.com.epicgames.account.oauth.authorization_pending":
                        pass
                    
                    elif error_code == "g":
                        pass
                    
                    elif error_code == "errors.com.epicgames.not_found":
                        bot.send_message(message.chat.id, f'❌ Login link expired, please use /login again.')
                        return None
                    else:
                        bot.send_message(message.chat.id, f'❌ Error occurred: {token_data.get("errorMessage", "Unknown error")}')
                        return None

                await asyncio.sleep(10)
            except ValueError as ve:
                print(f"Error with waiting for device code: {ve}")
                bot.send_message(message.chat.id, f'❌ An unexpected error occurred, please try again later.')
                return None
            except Exception as e:
                print(f"Unhandled exception: {e}")
                bot.send_message(message.chat.id, f'❌ An error occurred, please contact support.')
                return None

        try:
            async with self.http.request(
                method="GET",
                url=EpicEndpoints.endpoint_oauth_exchange,
                headers={"Authorization": f"bearer {token_data['access_token']}"},
            ) as request:
                if request.status != 200:
                    bot.send_message(message.chat.id, f'❌ Failed to retrieve exchange code. Please try again.')
                    return None

                exchange_data = await request.json()

            async with self.http.request(
                method="POST",
                url=EpicEndpoints.endpoint_prod03_oauth_token,
                headers={
                    "Authorization": f"basic {EPIC_API_IOS_CLIENT_TOKEN}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "grant_type": "exchange_code",
                    "exchange_code": exchange_data["code"]
                },
            ) as request:
                if request.status != 200:
                    bot.send_message(message.chat.id, f'❌ Failed to authenticate using exchange code. Please try again.')
                    return None

                auth_data = await request.json()

            return EpicUser(data=auth_data)

        except KeyError as ke:
            bot.send_message(message.chat.id, f'❌ Unexpected response format from server.')
            return None
        except Exception as e:
            print(f"Unhandled exception during token exchange: {e}")
            bot.send_message(message.chat.id, f'❌ An error occurred while completing authentication.')
            return None
        
    async def create_device_auths(self, user: EpicUser) -> dict:
        # creates device auth
        # REQUIRES usage of user.access_token as Authorization in headers
        async with self.http.request(
            method="POST",
            url=f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{user.account_id}/deviceAuth",
            headers={
                "Authorization": f"bearer {user.access_token}",
                "Content-Type": "application/json",
            },
        ) as request:
            data = await request.json()

        return {
            "device_id": data["deviceId"],
            "account_id": data["accountId"],
            "secret": data["secret"],
            "user_agent": data["userAgent"],
            "created": {
                "location": data["created"]["location"],
                "ip_address": data["created"]["ipAddress"],
                "datetime": data["created"]["dateTime"],
            },
        }
    
    async def get_account_metadata(self, user: EpicUser) -> json:
        # grabs account's metadata(basic information) from the api
        # REQUIRES usage of user.access_token as Authorization in headers

        url = f'https://account-public-service-prod03.ol.epicgames.com/account/api/public/account/displayName/{user.display_name}'
        headers = {
            "Authorization": f"bearer {user.access_token}",
            "Content-Type": "application/json",
        }

        async with self.http.get(url, headers=headers) as response:
            metadata = await response.json()

        return metadata

    async def get_external_connections(self, user: EpicUser) -> dict:
        # returns external connected accounts info
        # REQUIRES usage of user.access_token as Authorization in headers
        async with self.http.request(
            method="GET",
            url=f"https://account-public-service-prod03.ol.epicgames.com/account/api/public/account/{user.account_id}/externalAuths",
            headers={"Authorization": f"bearer {user.access_token}"}
        ) as resp:
            if resp.status != 200:
                return []
            
            external_auths = await resp.json()

        return external_auths
        
    async def get_public_account_info(self, user: EpicUser) -> dict:
        # returns basic public info about the account
        # REQUIRES usage of user.access_token as Authorization in headers
        url = f'https://account-public-service-prod03.ol.epicgames.com/account/api/public/account/{user.account_id}'
        headers = {
            "Authorization": f"bearer {user.access_token}"
        }

        async with self.http.get(url, headers=headers) as response:
            account_data = await response.json()
    
        account_info = {} # creating json for only stuff we are interested into
        creation_date = account_data.get("created", "?")
        if creation_date != "?":
            creation_date = datetime.strptime(creation_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d/%m/%Y")

        account_info['creation_date'] = creation_date
        account_info['externalAuths'] = await self.get_external_connections(user)
        return account_info
    
    async def get_common_profile(self, user: EpicUser) -> json:
        # gets the common profile, containing vbucks, receipts amount, vbucks purchases history, banners list
        # REQUIRES usage of user.access_token as Authorization in headers

        url = f'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{user.account_id}/client/QueryProfile?profileId=common_core&rvn=-1'
        headers = {
            "Authorization": f"bearer {user.access_token}",
            "Content-Type": "application/json"
        }

        profile_data = requests.post(url, headers=headers, json={}).json()
        return profile_data
    
    async def get_friend_codes(self, user: EpicUser, platform: str) -> json:
        # https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/v2/game/friendcodes/<accountID>/<platform>
        # gets the save the world redeem codes based on the platform you've entered
        # REQUIRES usage of user.access_token as Authorization in headers
        # this always returns an error saying page isn't found, im not sure why.
        url = f'https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/v2/game/friendcodes/{user.account_id}/{platform}'
        headers = {
            "Authorization": f"bearer {user.access_token}"
        }

        async with self.http.get(url, headers=headers) as response:
            codes_data = await response.json()
        
        return codes_data
    
    async def get_homebase_profile(self, user: EpicUser) -> json:
        # gets the save the world profile data
        # REQUIRES usage of user.access_token as Authorization in headers

        url = f'https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/profile/{user.account_id}/client/QueryPublicProfile'
        querystring = { "profileId":"campaign", "rvn":"-1" }
        payload = {}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"bearer {user.access_token}"
        }

        profile_data = requests.request("POST", url, json=payload, headers=headers, params=querystring).json()
        
        return profile_data
    
    async def set_affiliate(self, user: EpicUser, affiliate_name: str):
        url = f'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{user.account_id}/client/SetAffiliateName?profileId=common_core'
        payload = { "affiliateName": affiliate_name }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"bearer {user.access_token}"
        }
        
        affiliate_response = requests.request("POST", url, json=payload, headers=headers)
        
        if affiliate_response.status != 200:
            print(f"Error setting affiliate name ({affiliate_response.status})")
        
    async def get_locker_data(self, user: EpicUser) -> LockerData:
        # gets locker arrays
        # locker_categories - the locker categories we render
        url = f'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{user.account_id}/client/QueryProfile?profileId=athena'
        headers = {
            "Authorization": f"bearer {user.access_token}",
            "Content-Type": "application/json"
        }

        athena_data = requests.post(url, headers=headers, json={}).json()

        locker_data = LockerData()
        exclusive_cosmetics = []
        popular_cosmetics = []
        if "profileChanges" not in athena_data:
            return LockerData()   
        
        # activity
        account_level = athena_data.get("profileChanges", [{}])[0].get("profile", {}).get("stats", {}).get("attributes", {}).get("accountLevel", 1)
        last_match_end = athena_data.get("profileChanges", [{}])[0].get("profile", {}).get("stats", {}).get("attributes", {}).get("last_match_end_datetime", "")
        if last_match_end:
            last_match_end_date = datetime.fromisoformat(last_match_end.replace("Z", "+00:00"))
            days_since_last_match = (datetime.now(timezone.utc) - last_match_end_date).days
            last_match_date_str = last_match_end_date.strftime("%d.%m.%y")
            locker_data.last_match = f"{last_match_date_str} ({days_since_last_match} days ago)"
        else:
            locker_data.last_match = "800+ days ago"
            
        # getting extra cosmetics  
        try:
            with open('exclusive.txt', 'r', encoding='utf-8') as f:
                exclusive_cosmetics = [i.strip() for i in f.readlines()]

            with open('most_wanted.txt', 'r', encoding='utf-8') as f:
                popular_cosmetics = [i.strip() for i in f.readlines()]
        except FileNotFoundError:
            print("Warning: exclusive.txt or most_wanted.txt not found.")

        # getting owned items list
        for i in athena_data['profileChanges'][0]['profile']['items']:
            template_id = athena_data['profileChanges'][0]['profile']['items'][i]['templateId']
            if template_id.startswith('Athena'):
                cosmetic_category = template_id.split(':')[0]
                cosmetic_id = template_id.split(':')[1]
                locker_data.unlocked_styles[cosmetic_id] = []

                # adding missing categories to the arrays
                if 'AthenaExclusive' not in locker_data.cosmetic_categories:
                    locker_data.cosmetic_categories['AthenaExclusive'] = []
                    locker_data.cosmetic_array['AthenaExclusive'] = []
                    locker_data.cosmetic_categories['AthenaExclusive'].append(cosmetic_id)
                    
                if 'AthenaPopular' not in locker_data.cosmetic_categories:
                    locker_data.cosmetic_categories['AthenaPopular'] = []
                    locker_data.cosmetic_array['AthenaPopular'] = []
                    locker_data.cosmetic_categories['AthenaPopular'].append(cosmetic_id)
                    
                if 'HomebaseBannerIcons' not in locker_data.cosmetic_categories:
                    locker_data.cosmetic_categories['HomebaseBannerIcons'] = []
                    locker_data.cosmetic_array['HomebaseBannerIcons'] = []
                    locker_data.cosmetic_categories['HomebaseBannerIcons'].append(cosmetic_id)

                if cosmetic_category not in locker_data.cosmetic_categories:
                    locker_data.cosmetic_categories[cosmetic_category] = []
                    locker_data.cosmetic_array[cosmetic_category] = []
                locker_data.cosmetic_categories[cosmetic_category].append(cosmetic_id)  
                
        # listing the owned unlocked styles for each cosmetic
        for item_id, item_data in athena_data['profileChanges'][0]['profile']['items'].items():
            template_id = item_data.get('templateId', '')
            
            if template_id.startswith('Athena'):
                lowercase_cosmetic_id = template_id.split(':')[1]

                # adding the cosmetic to the "unlocked styles"
                if lowercase_cosmetic_id not in locker_data.unlocked_styles:
                    locker_data.unlocked_styles[lowercase_cosmetic_id] = []
        
                attributes = item_data.get('attributes', {})
                variants = attributes.get('variants', [])
                
                for variant in variants:
                    # adding the cosmetic's owned styles
                    locker_data.unlocked_styles[lowercase_cosmetic_id].extend(variant.get('owned', []))

        # getting banners
        common_profile_data = await self.get_common_profile(user)
        if common_profile_data:
            # common profile found
            for profileChange in common_profile_data["profileChanges"]:
                profile_items = profileChange["profile"]["items"]

                # checking every item
                for item_key, item_value in profile_items.items():
                    cosmetic_template_id = item_value.get("templateId", "")     
                    if cosmetic_template_id:
                        # the banner is found, so we adding it
                        lowercase_banner_id = cosmetic_template_id.split(':')[1]
                        if lowercase_banner_id not in locker_data.homebase_banners:
                            locker_data.homebase_banners[lowercase_banner_id] = []

        
        for category in locker_categories:
            if category == "AthenaPopular" or category == 'AthenaExclusive':
                continue
            
            try:
                list_of_cosmetic_ids = []
                # splitting the category's cosmetic ids to sublists
                for i in range(0, len(locker_data.cosmetic_categories[category]), 50):
                    sublist = locker_data.cosmetic_categories[category][i:i+50]
                    list_of_cosmetic_ids.append(sublist)

                for cosmetic_id in list_of_cosmetic_ids:
                    cosmetics_data = requests.get('https://fortnite-api.com/v2/cosmetics/br/search/ids?language=en&id={}'.format('&id='.join(cosmetic_id)))
                    c_data = cosmetics_data.json().get("data", [])
                    if not c_data:
                        # cosmetics data not found
                        continue

                    for cosmetic in c_data:
                        if cosmetic['id'] == "CID_DefaultOutfit":
                            # skipping default skin
                            continue
                        
                        if category == 'AthenaDance' and cosmetic['type']['value'] != 'emote' and cosmetic['id'] not in exclusive_cosmetics:
                            # emote category, but isnt exclusive and isnt emote
                            continue

                        make_mythic = False
                        if cosmetic['id'] in exclusive_cosmetics:
                            make_mythic = True
                            # Pink Ghoul Trooper
                            if cosmetic['id'].lower() == 'cid_029_athena_commando_f_halloween':
                                make_mythic = False
                                if 'Mat3' in locker_data.unlocked_styles.get('cid_029_athena_commando_f_halloween', []):
                                    make_mythic = True
                            
                            # Purple Skull Trooper
                            if cosmetic['id'].lower() == 'cid_030_athena_commando_m_halloween':
                                make_mythic = False
                                if 'Mat1' in locker_data.unlocked_styles.get('cid_030_athena_commando_m_halloween', []):
                                    make_mythic = True               
                            
                            # Aerial Assault Trooper
                            if cosmetic['id'].lower() == 'cid_017_athena_commando_m':
                                make_mythic = False
                                if 'Stage2' in locker_data.unlocked_styles.get('cid_017_athena_commando_m', []):
                                    make_mythic = True
                                    
                            # Renegade Raider
                            if cosmetic['id'].lower() == 'cid_028_athena_commando_f':
                                make_mythic = False
                                if 'Mat3' in locker_data.unlocked_styles.get('cid_028_athena_commando_f', []):
                                    make_mythic = True  
                                    
                            # Raider's Revenge
                            if cosmetic['id'].lower() == 'pickaxe_lockjaw':
                                make_mythic = False
                                if 'Stage2' in locker_data.unlocked_styles.get('pickaxe_lockjaw', []):
                                    make_mythic = True  
                                    
                            # Aerial Assault One
                            if cosmetic['id'].lower() == 'glider_id_001':
                                make_mythic = False
                                if 'Stage2' in locker_data.unlocked_styles.get('glider_id_001', []):
                                    make_mythic = True  
                                    
                            # Stage 5 Omega Lights
                            if cosmetic['id'].lower() == 'cid_116_athena_commando_m_carbideblack':
                                make_mythic = False
                                if 'Stage5' in locker_data.unlocked_styles.get('cid_116_athena_commando_m_carbideblack', []):
                                    make_mythic = True
                            
                            # Gold Midas
                            if cosmetic['id'].lower() == 'cid_694_athena_commando_m_catburglar':
                                make_mythic = False
                                if 'Stage4' in locker_data.unlocked_styles.get('cid_694_athena_commando_m_catburglar', []):
                                    make_mythic = True
                            
                            # Gold Meowscles
                            if cosmetic['id'].lower() == 'cid_693_athena_commando_m_buffcat':
                                make_mythic = False
                                if 'Stage4' in locker_data.unlocked_styles.get('cid_693_athena_commando_m_buffcat', []):
                                    make_mythic = True
                            
                            # Gold TNtina
                            if cosmetic['id'].lower() == 'cid_691_athena_commando_f_tntina':
                                make_mythic = False
                                if 'Stage7' in locker_data.unlocked_styles.get('cid_691_athena_commando_f_tntina', []):
                                    make_mythic = True
                                    
                            # Gold Skye
                            if cosmetic['id'].lower() == 'cid_690_athena_commando_f_photographer':
                                make_mythic = False
                                if 'Stage4' in locker_data.unlocked_styles.get('cid_690_athena_commando_f_photographer', []):
                                    make_mythic = True
                                    
                            # Gold Agent Peely
                            if cosmetic['id'].lower() == 'cid_701_athena_commando_m_bananaagent':
                                make_mythic = False
                                if 'Stage4' in locker_data.unlocked_styles.get('cid_701_athena_commando_m_bananaagent', []):
                                    make_mythic = True
                            
                            # World Cup Fishtick
                            if cosmetic['id'].lower() == 'cid_315_athena_commando_m_teriyakifish':
                                make_mythic = False
                                if 'Stage3' in locker_data.unlocked_styles.get('cid_315_athena_commando_m_teriyakifish', []):
                                    make_mythic = True
                            
                            # Mate Black Masterchief
                            if cosmetic['id'].lower() == 'cid_971_athena_commando_m_jupiter_s0z6m':
                                make_mythic = False
                                if 'Mat2' in locker_data.unlocked_styles.get('cid_971_athena_commando_m_jupiter_s0z6m', []):
                                    make_mythic = True
                            
                            if make_mythic == True:
                                cosmetic['rarity']['value'] = 'mythic'
                                
                        cosmetic_info = FortniteCosmetic()
                        cosmetic_info.cosmetic_id = cosmetic['id']
                        cosmetic_info.name = cosmetic['name']
                        cosmetic_info.small_icon = cosmetic['images']['smallIcon']
                        cosmetic_info.backend_value = category
                        cosmetic_info.rarity_value = cosmetic['rarity']['value']
                        cosmetic_info.is_banner = False
                        cosmetic_info.is_exclusive = make_mythic
                        cosmetic_info.is_popular = cosmetic['id'] in popular_cosmetics
                        cosmetic_info.unlocked_styles = locker_data.unlocked_styles[cosmetic['id'].lower()]

                        locker_data.cosmetic_array[category].append(cosmetic_info) 

                        # now special ones
                        if cosmetic_info.is_popular:
                            locker_data.cosmetic_array['AthenaPopular'].append(cosmetic_info)

                        if make_mythic:
                            locker_data.cosmetic_array['AthenaExclusive'].append(cosmetic_info)

            except Exception as e:
                print(f'exception: {e}')
                continue

        # handle banners
        banners_data = requests.get('https://fortnite-api.com/v1/banners')
        for fn_banner in banners_data.json()['data']:
            banner_lower_id = fn_banner['id'].lower()
            if banner_lower_id not in locker_data.homebase_banners:
                # banner isn't owned
                continue
            
            make_mythic = False
            icon = fn_banner['images']['icon']
            rarity = 'uncommon'
            if fn_banner['id'] in exclusive_cosmetics:
                make_mythic = True
                rarity = 'mythic'
                                    
            # for future
            cosmetic_info = FortniteCosmetic()
            cosmetic_info.cosmetic_id = fn_banner['id']
            cosmetic_info.name = fn_banner['devName']
            cosmetic_info.small_icon = fn_banner['images']['smallIcon']
            cosmetic_info.rarity_value = rarity
            cosmetic_info.backend_value = 'HomebaseBannerIcons'
            cosmetic_info.is_banner = True
            cosmetic_info.is_exclusive = make_mythic
            cosmetic_info.is_popular = fn_banner['id'] in popular_cosmetics
                
            locker_data.cosmetic_array['HomebaseBannerIcons'].append(cosmetic_info)      
            # now exclusive ones
            if make_mythic:
                locker_data.cosmetic_array['AthenaExclusive'].append(cosmetic_info)

        # sorting exclusives category
        locker_data.cosmetic_array['AthenaExclusive'].sort(
            key=lambda cosmetic: exclusive_cosmetics.index(cosmetic.cosmetic_id) 
            if cosmetic.cosmetic_id in exclusive_cosmetics 
            else float('inf')
        )

        # returning back the locker data
        return locker_data
    
    async def get_seasons_message(self, user: EpicUser) -> str:
        url = f'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{user.account_id}/client/QueryProfile?profileId=athena'
        headers = {
            "Authorization": f"bearer {user.access_token}",
            "Content-Type": "application/json"
        }

        athena_data = requests.post(url, headers=headers, json={}).json()

        past_seasons = {}
        seasons_info = []
            
        # seasons infos
        past_seasons = athena_data.get("profileChanges", [{}])[0].get("profile", {}).get("stats", {}).get("attributes", {}).get("past_seasons", [])
        total_wins = sum(season.get("numWins", 0) for season in past_seasons)
        total_matches = sum(
            season.get("numHighBracket", 0) + season.get("numLowBracket", 0) + 
            season.get("numHighBracket_LTM", 0) + season.get("numLowBracket_LTM", 0) + 
            season.get("numHighBracket_Ar", 0) + season.get("numLowBracket_Ar", 0) 
            for season in past_seasons
        )

        curses = athena_data.get("profileChanges", [{}])[0].get("profile", {}).get("stats", {}).get("attributes", {})
        cursesinfo = {
            'level': curses.get('level', 1),
            'book_level': curses.get('book_level', 1)
        }
            
        for season in past_seasons:
            seasons_info.append(f"""
#️⃣Season {season.get('seasonNumber', 1)}
› Level: {season.get('seasonLevel', '1')}
› Battle Pass: {bool_to_emoji(season.get('purchasedVIP', False))}
› Wins: {season.get('numWins', 0)}
            """)

        seasons_info_embeds = seasons_info
        seasons_info_message = "Previous Seasons History:\n" + "\n".join(seasons_info_embeds)
        seasons_info_message += f"\nCurrent Season:\n› Level: {cursesinfo['level']}\n› Battle Pass Level: {cursesinfo['book_level']}"
        return seasons_info_message