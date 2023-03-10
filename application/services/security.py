import sys
sys.path.append('/')
import env

# We should be importing Fernet to be used here, not through the env file

DISPATCHER = {
    "APP" : env.APP,
    "CAMERAS" : env.CAMERAS,
    "RECIPIENTS" : env.RECIPIENTS,
    "CREDENTIALS" : env.CREDENTIALS,
    "CARRIERS" : env.CARRIERS,
    "EXTERNAL_API" : env.EXTERNAL_API
}

def authenticate(username, password):
    """
    Takes an input value and verifies against encrypted value.
    """
    dec_user = __decrypt("CREDENTIALS", "user_login", "username")
    dec_pass = __decrypt("CREDENTIALS", "user_login", "password")

    if dec_user == -1 or dec_pass == -1 or dec_user != username or dec_pass != password:
        raise Exception("Failed to Authenticate Username or Password")

def get_value(env_var, key, field):
    """
    Reads from vault and returns decrypted value.
    """
    dec_val = ""
    try:
        dec_val = __decrypt(env_var, key, field)
    except Exception as e:
        raise e
    
    return dec_val

def get_keys(env_var, key=-1):
    """
    Reads from vault and returns env keys.
    """
    env_var = env_var.upper()
    try:
        if key == -1:
            # Return outer keys
            return DISPATCHER.get(env_var).keys()
        # Return inner keys
        return DISPATCHER.get(env_var).get(key).keys()

    except:
        raise Exception("Invalid environment variable or key name")

def put_value(env_var, key, field, val):
    # Restructure part of https://trello.com/c/22FPrkYW
    try:
        __encrypt(env_var, val, True, key, field)
    except Exception as e:
        raise Exception("PUT operation failed: \n" + str(e))

def __encrypt(env_var, val, write, key, field):
    """
    Encrypt data and enter into relevant location. 
    """
    encoded_msg = env.FERNET.encrypt(val.encode())
    
    # ME MAY NEED TO REMOVE THIS
    # Return encrypted value. Don't write to vault.
    if not write:
        return encoded_msg

    # Write encrypted value to vault.
    try:
        fetched_env = DISPATCHER.get(env_var.upper())
        fetched_env[key][field] = encoded_msg
    except Exception as e:
        raise Exception("Encryption failed: \n" + e)

def __decrypt(env_var, key, field):
    """
    Decrypt data using the specified key and index if relevant. Returns
    result.
    """
    dec_msg = ""
    enc_msg = ""

    try:
        enc_msg = DISPATCHER.get(env_var.upper()).get(key).get(field)
    except:
        raise Exception("Invalid parameters")
    
    dec_msg = -1 if enc_msg == "" else env.FERNET.decrypt(enc_msg).decode()
    return dec_msg

def main():
    # Utilize Symmetric-key Encryption.
    key = env.Fernet.generate_key()
    env.FERNET = env.Fernet(key)

    # Encrypt all sensitive data.
    for env_var in DISPATCHER:
        for key in DISPATCHER.get(env_var):
            for inner_key in DISPATCHER.get(env_var).get(key):
                data = DISPATCHER.get(env_var).get(key).get(inner_key)
                __encrypt(env_var, data, True, key, inner_key)

if __name__ == "application.services.security":
    main()
