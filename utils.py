def bool_to_emoji(value: bool):
    if value == True:
        return '✅';
    
    return '❌';

def country_to_flag(country_code):
    # thanks to Kayy
    if len(country_code) != 2:
        return country_code
    
    return chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397)

def mask_email(email):
    # thanks to Kayy
    if "@" in email:
        local_part, domain = email.split("@")
        if len(local_part) > 40:
            masked_local_part = local_part[0] + "*" * (len(local_part) - 40) + local_part[-40]

        elif len(local_part) == 2:
            masked_local_part = local_part[0] + "*"

        else:
            masked_local_part = local_part

        return f"{masked_local_part}@{domain}" 
    return email

def mask_account_id(account_id):
    # thanks to Kayy
    if len(account_id) > 32:
        return account_id[:16] + "*" * (len(account_id) - 32) + account_id[-16:]
    
    return account_id