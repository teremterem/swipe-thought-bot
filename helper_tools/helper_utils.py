import os

import yaml


def set_env_vars(for_local=False, project_dir='../'):
    set_env_vars_from_yml(f"{project_dir}serverless.env.yml")
    if for_local:
        set_env_vars_from_yml(f"{project_dir}serverless.env-local.yml")

    os.environ.setdefault('ES_REGION', os.environ['REGION'])
    os.environ.setdefault('TELEGRAM_CONV_STATE_DDB_TABLE_NAME', f"TelegramConvState-stb-{os.environ['STAGE']}")


def set_env_vars_from_yml(yml_filename):
    with open(yml_filename) as f:
        env_yml = yaml.safe_load(f)

    for k, v in env_yml.items():
        os.environ[k] = v
