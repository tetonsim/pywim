import os
import sys
import json

import pywim
import threemf

def get_smart_slice_job(tmf_path):
    tmf = threemf.ThreeMF()

    tmf_reader = threemf.io.Reader()
    tmf_reader.register_extension(pywim.smartslice.ThreeMFExtension)

    with open(tmf_path, 'rb') as tmf_bytes:
        tmf_reader.read(tmf, tmf_bytes)

    if len(tmf.extensions) != 1:
        raise Exception('3MF extension count is not 1')
    
    ext = tmf.extensions[0]

    job_assets = list(
        filter(lambda a: isinstance(a, pywim.smartslice.JobThreeMFAsset), ext.assets)
    )

    if len(job_assets) == 0:
        raise Exception('Could not find smart slice information in 3MF')

    return job_assets[0].content

def extract_smartslice_job(tmf_path):
    job : pywim.smartslice.job.Job = get_smart_slice_job(tmf_path)

    name, ext = os.path.splitext(tmf_path)

    with open(name + '.smart', 'w') as f:
        json.dump(job.to_dict(), f, indent=1)

def extract_chop_model(tmf_path):
    job : pywim.smartslice.job.Job = get_smart_slice_job(tmf_path)

    name, ext = os.path.splitext(tmf_path)

    with open(name + '.chp', 'w') as f:
        json.dump(job.chop.to_dict(), f, indent=1)

def main():
    if len(sys.argv) >= 3:
        if sys.argv[1] == 'extract-smartslice-job':
            return extract_smartslice_job(sys.argv[2])
        if sys.argv[1] == 'extract-chop-model':
            return extract_chop_model(sys.argv[2])
    return usage()

def usage():
    print('{} extract-smartslice-job 3MF'.format(sys.argv[0]))
    print('{} extract-chop-model 3MF'.format(sys.argv[0]))

if __name__ == '__main__':
    main()
