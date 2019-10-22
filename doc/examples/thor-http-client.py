import pywim
import pywim.http.thor as thor
import requests

def do_stuff(client):
    client.auth.token.put()

    creds = client.auth.whoami.get()

def new_smart_slice_run(client, tmfpath):
    # First, create information about our new task
    new_task = thor.NewTask(tmfpath)

    # Create the task on the server and get back the details of our task
    task = client.smart_slice.post(new_task)

    # Get a pre-signed URL to upload our 3MF for the task
    asset = client.smart_slice.file.post(id=task.id)

    # Upload the 3MF contents using the url
    with open(tmfpath, 'rb') as f:
        data = f.read()
        resp = requests.put(asset.url, data=data)

        if not resp.ok:
            print('Failed to upload 3MF for task %s' % task.id)
            print('Response: %i - %s' % resp.status_code, resp.text)
            return

    # Submit the task for execution
    submit_status = client.smart_slice.execute(id=task.id)

def main():
    client = thor.Client()

    print('Communicating with Thor server at: %s' % client.address)

    creds = client.auth.token.post(
        thor.LoginRequest('elon@spacex.com', 'm@rsorbust')
    )

    print('Hello %s %s' % (creds.user.first_name, creds.user.last_name))

    try:
        new_smart_slice_run(client, tmfpath='falcon-wing-bracket.3mf')
    finally:
        # Make sure we logout (deletes and invalidates the auth token)
        client.auth.token.delete()

if __name__ == '__main__':
    main()
