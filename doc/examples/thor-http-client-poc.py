import pywim
import time

import pywim.http.thor as thor

def main():
    # Read the 3MF file into bytes
    tmf_file = '/home/brady/Documents/SmartSlice/cube.3mf'
    with open(tmf_file, 'rb') as f:
        tmf_bytes = f.read()

    # Create the HTTP client with the default connection parameters
    client = thor.Client2019POC()

    # Submit the 3MF data for a new task
    task = client.submit.post(tmf_bytes)

    # While the task status is not finished or failed continue to periodically
    # check the status. This is a naive way of waiting, since this could take
    # a while (minutes).
    while task.status not in (thor.TaskStatus.finished, thor.TaskStatus.failed):
        time.sleep(0.05)
        task = client.status.get(id=task.id)

    if task.status == thor.TaskStatus.failed:
        print('Error: ', task.error)
    elif task.status == thor.TaskStatus.finished:
        # Get the task again, but this time with the results included
        task = client.result.get(id=task.id)
        print(task.to_dict())

if __name__ == '__main__':
    main()