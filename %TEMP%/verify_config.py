import yaml

with open('/c/pc/py/pyreview/PharmaSupplyBot/state/config.yaml') as f:
    data = yaml.safe_load(f)

ai = data.get('ai', {})
providers = ai.get('providers', {})
print(f'Total providers: {len(providers)}')
print()
print(f'{"provider":<12} {"YAML keys":<10} {"models":<8}')
print('-' * 35)
for name in sorted(providers.keys()):
    p = providers[name]
    env_keys = p.get('env_keys', [])
    models = p.get('models', [])
    print(f'{name:<12} {len(env_keys):<10} {len(models):<8}')
    print(f'  env_keys: {env_keys}')
    print()

# Also check that YAML env_keys are subsets of .env vars
import re
env_file = '/c/pc/py/pyreview/PharmaSupplyBot/.env'
env_vars = set()
try:
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key = line.split('=', 1)[0]
                env_vars.add(key)
except FileNotFoundError:
    print('No .env file')

print('=== Cross-check: YAML env_keys vs .env vars ===')
for name in sorted(providers.keys()):
    yaml_keys = providers[name].get('env_keys', [])
    missing = [k for k in yaml_keys if k not in env_vars]
    status = 'OK' if not missing else f'MISSING IN .env: {missing}'
    print(f'  {name:<12} {status}')