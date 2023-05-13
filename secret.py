def get_service_account(secret_id):
    import os,json
    #print(os.environ['gcp_secret'])
    from google.cloud import secretmanager
    os.environ['GOOGLE_APPLICATION_CREDENTIALS']=os.environ['gcp_secret']
    # print(json.load(open(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])))
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": secret_id})
    payload = response.payload.data.decode("UTF-8")
    #print("Plaintext: {}".format(payload))
    return json.loads(payload)
# print(get_service_account("projects/517186383841/secrets/demo_secret/versions/1"))