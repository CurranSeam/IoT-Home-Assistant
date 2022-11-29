import sys
sys.path.append('/')
import env

# We should be importing Fernet to be used here, not through the env file

def authenticate(data, key, index):
    """
    Takes an input value and verifies against encrypted value.
    """
    # WE DONT NEED TO ENCRYPT ANYMORE SINCE FERNET IS NOT A "DETERMINISTIC AUTHENTICATED CYPHER". THIS 
    # ENCRYPTED PASSWORD IS DIFFERENT THAN VAULT ENCRYPTED PASSWORD
    # enc_data = __encrypt(data, False)

    # if (key in env.CREDENTIALS.keys()):
    #     value = __get_value(env.CREDENTIALS, key, index)

    
    dec_pwd = __decrypt(key, index)

    if dec_pwd == -1 or dec_pwd != data:
        raise Exception("Failed to Authenticate Username or Password")

def __encrypt(val, write, key=-1, index=-1):
    """
    Encrypt data and enter into relevant location. 
    """
    encoded_msg = env.FERNET.encrypt(val.encode())
    
    # Return encrypted value. Don't write to vault.
    if not write:
        return encoded_msg

    # Write encrypted value to vault.
    if key in env.CAMERAS:
        env.CAMERAS[key] = encoded_msg
    elif key in env.RECIPIENTS:
        env.RECIPIENTS[key] = encoded_msg
    elif key in env.CREDENTIALS and index != -1:
        env.CREDENTIALS[key][index] = encoded_msg
    else:
        raise Exception("Invalid parameters")

def __decrypt(key, index=-1):
    """
    Decrypt data using the specified key and index if relevant. Returns
    result.
    """
    dec_msg = ""
    enc_msg = ""
    if key in env.CAMERAS:
        enc_msg = env.CAMERAS.get(key)
    elif key in env.RECIPIENTS:
        enc_msg = env.RECIPIENTS.get(key)
    elif key in env.CREDENTIALS and index in [0, 1]:
        values = env.CREDENTIALS.get(key)
        enc_msg = values[index]
    else:
        raise Exception("Invalid parameters")
    
    dec_msg = -1 if enc_msg == "" else env.FERNET.decrypt(enc_msg).decode()
    return dec_msg

def get_value(key, index=-1):
    """
    Reads from vault and returns decrypted value.
    """
    if index not in [-1, 0, 1]:
        raise Exception("Invalid index")
    elif index in [0, 1]:
        return __decrypt(key, index)
    return __decrypt(key)

def get_env(env_var):
    """
    Reads from vault and returns an env struct.
    Use in conjunction with get_value() to decrypt env values.
    """
    env_var = env_var.lower()
    if env_var == "cameras":
        return env.CAMERAS
    elif env_var == "recipients":
        return env.RECIPIENTS
    elif env_var == "credentials":
        return env.CREDENTIALS
    elif env_var == "carriers":
        return env.CARRIERS
    else:
        raise Exception("Invalid environment variable: " + env_var)

def main():
    # Utilize Symmetric-key Encryption.
    key = env.Fernet.generate_key()
    env.FERNET = env.Fernet(key)

    # Encrypt all sensitive data.
    for cam in env.CAMERAS:
        data = env.CAMERAS.get(cam)
        __encrypt(data, True, cam)

    for recipient in env.RECIPIENTS:
        data = env.RECIPIENTS.get(recipient)
        __encrypt(data, True, recipient)

    for cred in env.CREDENTIALS:
        data = env.CREDENTIALS.get(cred)
        for count, val in enumerate(data):
            __encrypt(val, True, cred, count)

if __name__=="__main__":
    main()
