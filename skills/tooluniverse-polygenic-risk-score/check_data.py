import sys
sys.path.insert(0, 'src')
from tooluniverse.tools import gwas_get_associations_for_trait
import json

result = gwas_get_associations_for_trait(disease_trait='type 2 diabetes', size=2)
if result and 'data' in result:
    print(json.dumps(result['data'][0], indent=2))
