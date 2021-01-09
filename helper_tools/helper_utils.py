import os

import yaml


# TODO oleksandr: unhardcode backend_stage='oleksandr'
def set_env_vars(project_dir='../', backend_stage='oleksandr', local_overlay=False):
    set_env_vars_from_yml(f"{project_dir}serverless.env-{backend_stage}.yml")
    if local_overlay:
        set_env_vars_from_yml(f"{project_dir}serverless.env-local.yml")

    os.environ.setdefault('STAGE', backend_stage)
    os.environ.setdefault('REGION', 'us-east-1')
    os.environ.setdefault('ES_REGION', os.environ['REGION'])
    os.environ.setdefault('SWIPER_CHAT_DATA_DDB_TABLE_NAME', f"SwiperChatData-stb-{os.environ['STAGE']}")
    os.environ.setdefault('MAIN_S3_BUCKET_NAME', f"stb-{os.environ['STAGE']}")


def set_env_vars_from_yml(yml_filename):
    with open(yml_filename) as f:
        env_yml = yaml.safe_load(f)

    for k, v in env_yml.items():
        os.environ[k] = v
