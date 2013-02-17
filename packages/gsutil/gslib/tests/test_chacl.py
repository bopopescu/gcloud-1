# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import time

from gslib.command import _ThreadedLogger as ThreadedLogger
import gslib.commands.chacl as chacl
import gslib.tests.testcase as case
from gslib.tests.util import ObjectToURI as suri


class ChaclIntegrationTest(case.GsUtilIntegrationTestCase):
  """Tests gslib.commands.chacl."""
  logger = ThreadedLogger()

  def setUp(self):
    super(ChaclIntegrationTest, self).setUp()
    self.sample_uri = self.CreateBucket()
    self.logger = ThreadedLogger()

  def testAclChangeWithUserId(self):
    change = chacl.AclChange(self.USER_TEST_ID + ':r',
                             scope_type=chacl.ChangeType.USER,
                             logger=self.logger)
    acl = self.sample_uri.get_acl()
    change.Execute(self.sample_uri, acl)
    self._AssertHas(acl, 'READ', 'UserById', self.USER_TEST_ID)

  def testAclChangeWithGroupId(self):
    change = chacl.AclChange(self.GROUP_TEST_ID + ':r',
                             scope_type=chacl.ChangeType.GROUP,
                             logger=self.logger)
    acl = self.sample_uri.get_acl()
    change.Execute(self.sample_uri, acl)
    self._AssertHas(acl, 'READ', 'GroupById', self.GROUP_TEST_ID)

  def testAclChangeWithUserEmail(self):
    change = chacl.AclChange(self.USER_TEST_ADDRESS + ':r',
                             scope_type=chacl.ChangeType.USER,
                             logger=self.logger)
    acl = self.sample_uri.get_acl()
    change.Execute(self.sample_uri, acl)
    self._AssertHas(acl, 'READ', 'UserByEmail', self.USER_TEST_ADDRESS)

  def testAclChangeWithGroupEmail(self):
    change = chacl.AclChange(self.GROUP_TEST_ADDRESS + ':fc',
                             scope_type=chacl.ChangeType.GROUP,
                             logger=self.logger)
    acl = self.sample_uri.get_acl()
    change.Execute(self.sample_uri, acl)
    self._AssertHas(acl, 'FULL_CONTROL', 'GroupByEmail',
                    self.GROUP_TEST_ADDRESS)

  def testAclChangeWithDomain(self):
    change = chacl.AclChange(self.DOMAIN_TEST + ':READ',
                             scope_type=chacl.ChangeType.GROUP,
                             logger=self.logger)
    acl = self.sample_uri.get_acl()
    change.Execute(self.sample_uri, acl)
    self._AssertHas(acl, 'READ', 'GroupByDomain', self.DOMAIN_TEST)

  def testAclChangeWithAllUsers(self):
    change = chacl.AclChange('AllUsers:WRITE',
                             scope_type=chacl.ChangeType.GROUP,
                             logger=self.logger)
    acl = self.sample_uri.get_acl()
    change.Execute(self.sample_uri, acl)
    self._AssertHas(acl, 'WRITE', 'AllUsers')

  def testAclChangeWithAllAuthUsers(self):
    change = chacl.AclChange('AllAuthenticatedUsers:READ',
                             scope_type=chacl.ChangeType.GROUP,
                             logger=self.logger)
    acl = self.sample_uri.get_acl()
    change.Execute(self.sample_uri, acl)
    self._AssertHas(acl, 'READ', 'AllAuthenticatedUsers')

  def testAclDelWithUser(self):
    add = chacl.AclChange(self.USER_TEST_ADDRESS + ':READ',
                          scope_type=chacl.ChangeType.USER,
                          logger=self.logger)
    acl = self.sample_uri.get_acl()
    add.Execute(self.sample_uri, acl)
    self._AssertHas(acl, 'READ', 'UserByEmail', self.USER_TEST_ADDRESS)

    remove = chacl.AclDel(self.USER_TEST_ADDRESS,
                          logger=self.logger)
    remove.Execute(self.sample_uri, acl)
    self._AssertHasNo(acl, 'READ', 'UserByEmail', self.USER_TEST_ADDRESS)

  def testAclDelWithGroup(self):
    add = chacl.AclChange(self.USER_TEST_ADDRESS + ':READ',
                          scope_type=chacl.ChangeType.GROUP,
                          logger=self.logger)
    acl = self.sample_uri.get_acl()
    add.Execute(self.sample_uri, acl)
    self._AssertHas(acl, 'READ', 'GroupByEmail', self.USER_TEST_ADDRESS)

    remove = chacl.AclDel(self.USER_TEST_ADDRESS,
                          logger=self.logger)
    remove.Execute(self.sample_uri, acl)
    self._AssertHasNo(acl, 'READ', 'GroupByEmail', self.GROUP_TEST_ADDRESS)

  #
  # Here are a whole lot of verbose asserts
  #

  def _AssertHas(self, current_acl, perm, scope, value=None):
    matches = list(self._YieldMatchingEntries(current_acl, perm, scope, value))
    self.assertEqual(1, len(matches))

  def _AssertHasNo(self, current_acl, perm, scope, value=None):
    matches = list(self._YieldMatchingEntries(current_acl, perm, scope, value))
    self.assertEqual(0, len(matches))

  def _YieldMatchingEntries(self, current_acl, perm, scope, value=None):
    """Generator that finds entries that match the change descriptor."""
    for entry in current_acl.entries.entry_list:
      if entry.scope.type == scope:
        if scope in ['UserById', 'GroupById']:
          if value == entry.scope.id:
            yield entry
        elif scope in ['UserByEmail', 'GroupByEmail']:
          if value == entry.scope.email_address:
            yield entry
        elif scope == 'GroupByDomain':
          if value == entry.scope.domain:
            yield entry
        elif scope in ['AllUsers', 'AllAuthenticatedUsers']:
          yield entry
        else:
          raise CommandException('Found an unrecognized ACL '
                                 'entry type, aborting.')

  def _MakeScopeRegex(self, scope_type, email_address, perm):
    template_regex = (
        r'<Scope type="{0}">\s*<EmailAddress>\s*{1}\s*</EmailAddress>\s*'
        r'</Scope>\s*<Permission>\s*{2}\s*</Permission>')
    return template_regex.format(scope_type, email_address, perm)

  def testBucketAclChange(self):
    test_regex = self._MakeScopeRegex(
        'UserByEmail', self.USER_TEST_ADDRESS, 'FULL_CONTROL')
    xml = self.RunGsUtil(
        ['getacl', suri(self.sample_uri)], return_stdout=True)
    self.assertNotRegexpMatches(xml, test_regex)

    self.RunGsUtil(
        ['chacl', '-u', self.USER_TEST_ADDRESS+':fc', suri(self.sample_uri)])
    xml = self.RunGsUtil(
        ['getacl', suri(self.sample_uri)], return_stdout=True)
    self.assertRegexpMatches(xml, test_regex)

    self.RunGsUtil(
        ['chacl', '-d', self.USER_TEST_ADDRESS, suri(self.sample_uri)])
    xml = self.RunGsUtil(
        ['getacl', suri(self.sample_uri)], return_stdout=True)
    self.assertNotRegexpMatches(xml, test_regex)

  def testObjectAclChange(self):
    obj = self.CreateObject(bucket_uri=self.sample_uri, contents='something')
    test_regex = self._MakeScopeRegex(
        'GroupByEmail', self.GROUP_TEST_ADDRESS, 'READ')
    xml = self.RunGsUtil(['getacl', suri(obj)], return_stdout=True)
    self.assertNotRegexpMatches(xml, test_regex)

    self.RunGsUtil(['chacl', '-g', self.GROUP_TEST_ADDRESS+':READ', suri(obj)])
    xml = self.RunGsUtil(['getacl', suri(obj)], return_stdout=True)
    self.assertRegexpMatches(xml, test_regex)

    self.RunGsUtil(['chacl', '-d', self.GROUP_TEST_ADDRESS, suri(obj)])
    xml = self.RunGsUtil(['getacl', suri(obj)], return_stdout=True)
    self.assertNotRegexpMatches(xml, test_regex)

  def testMultithreadedAclChange(self, count=10):
    objects = []
    for i in range(count):
      objects.append(self.CreateObject(
          bucket_uri=self.sample_uri,
          contents='something {0}'.format(i)))

    test_regex = self._MakeScopeRegex(
        'GroupByEmail', self.GROUP_TEST_ADDRESS, 'READ')
    xmls = []
    for obj in objects:
      xmls.append(self.RunGsUtil(['getacl', suri(obj)], return_stdout=True))
    for xml in xmls:
      self.assertNotRegexpMatches(xml, test_regex)

    uris = [suri(obj) for obj in objects]
    self.RunGsUtil(['-m', '-DD', 'chacl', '-g',
                    self.GROUP_TEST_ADDRESS+':READ'] + uris)

    xmls = []
    for obj in objects:
      xmls.append(self.RunGsUtil(['getacl', suri(obj)], return_stdout=True))
    for xml in xmls:
      self.assertRegexpMatches(xml, test_regex)

  def testMultiVersionSupport(self):
    bucket = self.CreateVersionedBucket()
    object_name = self.MakeTempName('obj')
    obj = self.CreateObject(
        bucket_uri=bucket, object_name=object_name, contents='One thing')
    # Create another on the same URI, giving us a second version.
    self.CreateObject(
        bucket_uri=bucket, object_name=object_name, contents='Another thing')
    # Bucket listings are eventually consistent, so wait to increase the likelihood 
    # we'll see both versions of the object we just created. 
    time.sleep(0.5)
    stdout = self.RunGsUtil(['ls', '-a', suri(obj)], return_stdout=True)
    obj_v1, obj_v2 = stdout.strip().split('\n')

    test_regex = self._MakeScopeRegex(
        'GroupByEmail', self.GROUP_TEST_ADDRESS, 'READ')
    xml = self.RunGsUtil(['getacl', obj_v1], return_stdout=True)
    self.assertNotRegexpMatches(xml, test_regex)

    self.RunGsUtil(['chacl', '-g', self.GROUP_TEST_ADDRESS+':READ', obj_v1])
    xml = self.RunGsUtil(['getacl', obj_v1], return_stdout=True)
    self.assertRegexpMatches(xml, test_regex)

    xml = self.RunGsUtil(['getacl', obj_v2], return_stdout=True)
    self.assertNotRegexpMatches(xml, test_regex)
