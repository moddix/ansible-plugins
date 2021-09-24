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
    import boto
    import boto.cloudformation
except ImportError:
    raise AnsibleError("Can't lookup cloudformation, boto module not installed")


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
         'region' : 'eu-west-1',
         'profile': None,
         'stack': None
      }
      params.update(stack_sections)

      # check all supplied parameters are valid
      name = None
      for term in terms:
         try:
            name, value = term.split('=')
            assert(name in params)
            params[name] = value
         except (ValueError, AssertionError) as e:
            if name:
               raise AnsibleError("Invalid cloudformation lookup param: " + name)
            else:
               raise AnsibleError("Cloudformation lookup syntax error")

      # check only one stack section identifier supplied
      count = 0
      for stack_section in stack_sections:
         if params[stack_section] is not None:
            count += 1
            section = stack_section
            key = params[section]
      if count != 1:
         raise AnsibleError("Either 'output', 'parameter', or 'resource_id' \
             must be specified but not more than one")

      stack = memoized_stacks.get(params['region'] + params['profile'] + params['stack'])
      if not stack:
          conn = boto.cloudformation.connect_to_region(params['region'],
                profile_name=params['profile'])
          stack = conn.describe_stacks(stack_name_or_id=params['stack'])[0]
          memoized_stacks[params['region'] + params['profile'] + params['stack']] = stack

      if section in ['parameter', 'output']:
         attr = "{0}s".format(section)
         return [item.value for item in getattr(stack, attr) if item.key == key]
      elif section == 'resource_id':
         return [stack.describe_resources(key)[0].physical_resource_id]
      else:
         raise AnsibleError("unknown resource type {0}".format(section))
