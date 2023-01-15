from lib.system_utils import exc
import ast,requests,time,copy,json
from packaging import version


def get_grype_vulns(sbom_path:str,packages:list,extended_vulns:list=[], add_cpes_if_none:bool=False):
    vulns = exc(f'wsl grype sbom:{sbom_path} --add-cpes-if-none -o table ' if add_cpes_if_none else f'wsl grype sbom:{sbom_path} -o table')
    if 'No vulnerabilities found' in vulns:
        return [],[]

    data=[line.split() for line in vulns.splitlines()]

    while not(data[0][0]=='NAME') and len(data)>0:
        data=data[1:]
    for idx,row in enumerate(data):
        if len(row)<6:
            data[idx]=row[:2]+['']+row[2:] 
    
    data=data[1:]
        
    vulnerabilities = list()
    grype_pot_affection = list()
    for vuln in data:
        if vuln[0].lower() in [p['name'].lower() for p in packages]:
            v= extend_vulns_with_grypedb([{
                'namespace':vuln[4].split('-')[0],
                'url':'',
                'severity':vuln[5].upper() if vuln[5].upper()!='MODERATE' else 'MEDIUM',
                'fixed_package_version':vuln[2],
                'other_sources':'',
                'source':'GRYPE',
                'id':vuln[4]
            }],extended_vulns).pop()
            vulnerabilities.append(v)
            grype_pot_affection.append({
                'vulnerability':v['id'],
                'package':[p['purl'] for p in packages if p['name'].lower()==vuln[0].lower()].pop()
            })

    return vulnerabilities, grype_pot_affection




def extend_vulns_with_grypedb(vulns:list, grype_extended_vulns:list):
    result = copy.deepcopy(vulns)

    for vuln in result:
        ext = [v for v in grype_extended_vulns if vuln['id']==v['id']]
        if len(ext)==0:
            continue
        for related in ast.literal_eval(ext.pop()['related_vulnerabilities']):
            if related['namespace'] == 'nvd:cpe' and vuln['namespace']!='CVE':
                vuln['id'], vuln['other_sources'] = related['id'], vuln['id']
                vuln['namespace']='CVE'
    
        vuln['url'] = 'https://github.com/advisories/{}'.format(vuln['id']) if vuln['namespace']=='GHSA' else vuln['url']
        vuln['url'] = 'https://nvd.nist.gov/vuln/detail/{}'.format(vuln['id']) if vuln['namespace']=='CVE' else vuln['url']
    return result


def is_vulnerable(version_constraint:str, ver:str):
    is_vuln = False
    vers_vector= version_constraint.replace('>','').replace('<','').split(',')
    if len(vers_vector)==1:
            if '=' not in version_constraint:
                if '<' in version_constraint:
                    is_vuln = version.parse(ver)<version.parse(vers_vector[0])
                elif '>' in version_constraint:
                    is_vuln = version.parse(ver)>version.parse(vers_vector[0])
            elif '='  in version_constraint:
                if '<' not in version_constraint and '>' not in version_constraint:
                    is_vuln=version.parse(ver)==version.parse(vers_vector[0].replace('=',''))
                
                elif '<' in version_constraint:
                    is_vuln= version.parse(ver)<=version.parse(vers_vector[0].replace('=',''))
                elif '>' in version_constraint:
                    is_vuln= version.parse(ver)>=version.parse(vers_vector[0].replace('=',''))
    
    elif len(vers_vector)==2:
            if '=' in vers_vector[0] and '=' in vers_vector[1]:
                is_vuln = version.parse(ver)>=version.parse(vers_vector[0].replace('=','')) and version.parse(ver)<=version.parse(vers_vector[1].replace('=',''))

            elif '=' in vers_vector[0] and '=' not in vers_vector[1]:
                is_vuln = version.parse(ver)>=version.parse(vers_vector[0].replace('=','')) and version.parse(ver)<version.parse(vers_vector[1])
 
            elif '=' not in vers_vector[0] and '=' not in vers_vector[1]:
                is_vuln = version.parse(ver)>version.parse(vers_vector[0]) and version.parse(ver)<version.parse(vers_vector[1])

            elif '=' not in vers_vector[0] and '=' in vers_vector[1]:
                is_vuln = version.parse(ver)>version.parse(vers_vector[0]) and version.parse(ver)<=version.parse(vers_vector[1].replace('=',''))

    return is_vuln



# The public rate limit (without an API key) is 5 requests in a rolling 30 second window, thus the default wait_time is setted to 6 sec
# Source: https://nvd.nist.gov/developers/start-here#:~:text=The%20public%20rate%20limit%20(without,a%20rolling%2030%20second%20window

def extend_vulns_with_nvdapi(vulns:list,wait_time:int=6,logger:object=None, nvd_api_key:str=None):
    vulnerabilities = copy.deepcopy(vulns)
    for vuln in vulnerabilities:
        if logger is not None: logger.info('Contacting OSV API for vulnerability "{}"...'.format(vuln['id']))
        time.sleep(wait_time)
        if vuln['namespace'] != 'CVE':
            continue
        metadata = requests.get('https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={}'.format(vuln['id']),headers={'apiKey':nvd_api_key}) if nvd_api_key else requests.get('https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={}'.format(vuln['id']))
        try:
            metadata = metadata.json()
        except Exception as e:
            continue
        
        if 'vulnerabilities' not in metadata or len(metadata['vulnerabilities'])<1:
            if logger is not None: logger.warn('Failed to parse OSV API response for vulnerability  "{}". \n Problem: {} \n Response: {}'.format(vuln['id'],e,metadata))
            continue

        metadata = metadata['vulnerabilities'].pop()

        if 'cve' not in metadata:
            continue

        metadata = metadata['cve']

        if 'descriptions' in metadata and len([d for d in metadata['descriptions'] if 'lang' in d and 'value' in d and d['lang']=='en']):
            vuln['description'] = [d['value'] for d in metadata['descriptions'] if d['lang']=='en'].pop().replace('"',"'")
 
        if 'published' in metadata:
            vuln['published_at'] =metadata['published'] 
            
        if 'metrics' in metadata and 'cvssMetricV31' in metadata['metrics'] and len (metadata['metrics']['cvssMetricV31'])>0:
            cvss_metrics= metadata['metrics']['cvssMetricV31'][0]
            vuln['exploitability_score']=cvss_metrics['exploitabilityScore'] if 'exploitabilityScore' in cvss_metrics else ''
            vuln['impact_score']=cvss_metrics['impactScore'] if 'impactScore' in cvss_metrics else ''
            if 'cvssData' in cvss_metrics:
                cvssData=cvss_metrics['cvssData']
                vuln['attack_vector'] =cvssData['attackVector'] if 'attackVector' in cvssData else ''
                vuln['attack_complexity'] =cvssData['attackComplexity'] if 'attackComplexity' in cvssData else ''
                vuln['priviledge_required'] =cvssData['privilegesRequired'] if 'privilegesRequired' in cvssData else ''
                vuln['user_interaction'] =cvssData['userInteraction'] if 'userInteraction' in cvssData else ''
                vuln['scope'] =cvssData['scope'] if 'scope' in cvssData else ''
                vuln['confidentiality_impact'] =cvssData['confidentialityImpact'] if 'confidentialityImpact' in cvssData else ''
                vuln['integrity_impact'] =cvssData['integrityImpact'] if 'integrityImpact' in cvssData else ''
                vuln['availability_impact'] =cvssData['availabilityImpact'] if 'availabilityImpact' in cvssData else ''
                vuln['base_score'] =cvssData['baseScore'] if 'baseScore' in cvssData else ''
                if 'baseSeverity' in cvssData:
                    vuln['severity'] =cvssData['baseSeverity']
                vuln['vector_string'] = cvssData['vectorString'] if 'vectorString' in cvssData else ''
        
        elif 'metrics' in metadata and 'cvssMetricV2' in metadata['metrics'] and len (metadata['metrics']['cvssMetricV2'])>0:
            cvss_metrics= metadata['metrics']['cvssMetricV2'][0]
            vuln['exploitability_score']=cvss_metrics['exploitabilityScore'] if 'exploitabilityScore' in cvss_metrics else ''
            vuln['impact_score']=cvss_metrics['impactScore'] if 'impactScore' in cvss_metrics else ''
            if 'cvssData' in cvss_metrics:
                cvssData=cvss_metrics['cvssData']
                vuln['attack_vector'] =cvssData['accessVector'] if 'accessVector' in cvssData else ''
                vuln['attack_complexity'] =cvssData['accessComplexity'] if 'accessComplexity' in cvssData else ''
                vuln['confidentiality_impact'] =cvssData['confidentialityImpact'] if 'confidentialityImpact' in cvssData else ''
                vuln['integrity_impact'] =cvssData['integrityImpact'] if 'integrityImpact' in cvssData else ''
                vuln['availability_impact'] =cvssData['availabilityImpact'] if 'availabilityImpact' in cvssData else ''
                vuln['base_score'] =cvssData['baseScore'] if 'baseScore' in cvssData else ''
                if 'baseSeverity' in cvssData:
                    vuln['severity'] =cvssData['baseSeverity']
                vuln['vector_string'] = cvssData['vectorString'] if 'vectorString' in cvssData else ''
    return vulnerabilities


def get_osv_api_vulnerabilities (package:dict,wait_response_time:int=2,logger:object=None):
    vulnerabilities,affections = list(),list()
    # From PURL code to OSV API code (https://ossf.github.io/osv-schema/#affectedpackage-field)
    ecosystem_dictionary = dict(zip(['golang','npm','nuget','pypi','gem','maven','cargo'],['Go','npm','NuGet','PyPI','RubyGems','Maven','crates.io']))
    package_name = package['name'] + ':' + package['namespace'] if package['namespace']!='' else package['name']
    if logger: logger.info(f'Contacting OSV API for vulnerabilities in package "{package_name}"...')

    if package['package_manager'] not in ecosystem_dictionary:
        return [],[]
    while(True):
        try:
            result = requests.post('https://api.osv.dev/v1/query', json= {'version':package['version'],
                                                                          'package':{'name':package_name,'ecosystem':ecosystem_dictionary[package['package_manager']]}})
            break
        except Exception as e:
            if logger: logger.warning(f'Timeout error while contacting OSV API for package "{package_name}. Waiting {wait_response_time} seconds before another trial."')
            time.sleep(wait_response_time)
            
    if (result.status_code!=200):
        if logger: logger.warning(f'OSV API replied with status code "{result.status_code}" for package "{package_name}". \n Response: {result}')
        return [],[]
    result=json.loads(result.text)
    if result=={}:
        return [],[]

    if 'vulns' not in result:
        if logger: logger.warning(f'OSV API replied with not-well-formed response for package "{package_name}". \n Response: {result}')
        return [],[]
    
    for vuln in result['vulns']:

        ids = [vuln['id']]
        if 'aliases' in vuln: ids.extend([alias for alias in vuln['aliases']])

        other_sources,id = '',vuln['id']
        for element in ids:
            if element.startswith('CVE'):
                id = element 
            else:
                other_sources = element
                
        url=f'https://nvd.nist.gov/vuln/detail/{id}' if id.startswith('CVE') else f'https://github.com/advisories/{id}' if id.startswith('GHSA') else ''
        if not url and 'references' in vuln and len(vuln['references'])>0:
            for reference in vuln['references']:
                if 'url' in reference:
                    url = reference['url']
                    break

        fixed_package_version_vector={'fixed':list(),'from_last_affected':list()}
        if 'affected' in vuln:
            for affected_package in vuln['affected']:
                if 'package' in affected_package and 'name' in affected_package['package'] and 'ecosystem' in affected_package['package'] and package_name in affected_package['package']['name'] and affected_package['package']['ecosystem']==ecosystem_dictionary[package['package_manager']]:
                        if 'ranges' in affected_package:
                            for vers_range in affected_package['ranges']:
                                if 'events' in vers_range and len(vers_range['events'])>0:
                                    for event in vers_range['events']:
                                        if 'fixed' in event:
                                            fixed_package_version_vector['fixed'].append(event['fixed'])
                                        elif 'last_affected' in event:    
                                            fixed_package_version_vector['from_last_affected'].append('.'.join(event['last_affected'].split('.')[:len(event['last_affected'].split('.'))-1]) +'.'+ str(int(event['last_affected'].split('.')[len(event['last_affected'].split('.'))-1])+1))
        
        fixed_package_version = '0.0.0'
        for vers in fixed_package_version_vector['from_last_affected'] + fixed_package_version_vector['fixed']:
            if version.parse(vers)>version.parse(fixed_package_version):
                fixed_package_version = vers
        fixed_package_version = '' if fixed_package_version == '0.0.0' else fixed_package_version

        vulnerabilities.append({
            'namespace': id.split('-')[0],
            'url':url,
            'severity': (vuln['database_specific']['severity'].upper() if vuln['database_specific']['severity'].upper()!='MODERATE' else 'MEDIUM') if 'database_specific' in vuln and 'severity' in vuln['database_specific'] else '',
            'fixed_package_version':fixed_package_version,
            'other_sources': other_sources,
            'source':'OSV_API',
            'id':id
        })
        affections.append({
                'vulnerability':id,
                'package':package['purl']
            })

    return vulnerabilities,affections