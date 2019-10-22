import pywim
import pywim.http.thor as thor
import requests

def do_stuff(client):
    client.auth.token.put()

    creds = client.auth.whoami.get()

def new_smart_slice_run(client, tmfpath):
    # First, create information about our new job
    new_job = thor.NewSmartSliceJob(tmfpath, pywim.smartslice.job.JobType.validation)

    # Create the job on the server and get back the details of our job
    job = client.smart_slice.post(new_job)

    # Get a pre-signed URL to upload our 3MF for the job
    url = client.smart_slice.file.post(id=job.id)

    # Upload the 3MF contents using the url
    with open(tmfpath, 'rb') as f:
        data = f.read()
        resp = requests.put(url, data=data)

        if not resp.ok:
            print('Failed to upload 3MF for job %s' % job.id)
            print('Response: %i - %s' % resp.status_code, resp.text)
            return

    # Submit the job for execution
    submit_status = client.smart_slice.execute(id=job.id)

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
