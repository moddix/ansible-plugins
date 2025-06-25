# (c) 2014, Dean Wilson <dean.wilson(at)gmail.com>
# (c) 2016, Daniel Butler <rubbish(at)kefa.co.uk>
# 
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
# Refactored for Ansible 2.0 by Josh Quint  josh at turinggroup.com

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

try:
    import boto3
    import botocore
except ImportError:
    raise AnsibleError("Can't lookup cloudformation, boto3 module not installed")

memoized_stacks = {}


class LookupModule(LookupBase):

    def run(self, terms, variables, **kwargs):

        # defined allowed input parameters
        stack_sections = {
            'output': None,
            'resource_id': None,
            'parameter': None
        }
        params = {
            'region': 'eu-west-1',
            'profile': None,
            'stack': None
        }
        params.update(stack_sections)

        # check all supplied parameters are valid
        name = None
        for term in terms:
            try:
                name, value = term.split('=')
                assert (name in params)
                params[name] = value
            except (ValueError, AssertionError) as e:
                if name:
                    raise AnsibleError("Invalid cloudformation lookup param: " + name)
                else:
                    raise AnsibleError("Cloudformation lookup syntax error")

        # check only one stack section identifier supplied
        count = 0
        section = None
        for stack_section in stack_sections:
            if params[stack_section] is not None:
                count += 1
                section = stack_section
                key = params[section]
        if count != 1:
            raise AnsibleError("Either 'output', 'parameter', or 'resource_id' \
             must be specified but not more than one")

        cache_key = params['region'] + str(params['profile']) + params['stack']
        stack = memoized_stacks.get(cache_key)

        try:
            try:
                if params['profile']:
                    session = boto3.Session(region_name=params['region'], profile_name=params['profile'])
                else:
                    session = boto3.Session(region_name=params['region'])
            except botocore.exceptions.ProfileNotFound as e:
                # try env vars instead
                session = boto3.Session(region_name=params['region'])
                
            client = session.client('cloudformation')

            if not stack:
                response = client.describe_stacks(StackName=params['stack'])
                stack = response['Stacks'][0]
                memoized_stacks[cache_key] = stack

            if section == 'output':
                return [o['OutputValue'] for o in stack.get('Outputs', []) if o['OutputKey'] == key]

            elif section == 'parameter':
                return [p['ParameterValue'] for p in stack.get('Parameters', []) if p['ParameterKey'] == key]

            elif section == 'resource_id':
                resources = client.describe_stack_resources(StackName=params['stack'])['StackResources']
                return [r['PhysicalResourceId'] for r in resources if r['LogicalResourceId'] == key]

            else:
                raise AnsibleError(f"unknown resource type {section}")

        except botocore.exceptions.ClientError as e:
            raise AnsibleError(f"Failed to describe stack: {str(e)}")

