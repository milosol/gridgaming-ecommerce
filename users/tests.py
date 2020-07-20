# from django.test import TestCase
#
# # Create your tests here.
# class TestTwitterLogin(StaticLiveServerTestCase):
#     fixtures = ['allauth_fixture']
#
#     def setUp(self):
#         self.browser = webdriver.Firefox()
#         self.browser.implicitly_wait(3)
#         self.browser.wait = WebDriverWait(self.browser, 10)
#         activate('en')
#
#     def tearDown(self):
#         self.browser.quit()
#
#     def get_element_by_id(self, element_id):
#         return self.browser.wait.until(EC.presence_of_element_located(
#             (By.ID, element_id)))
#
#     def get_button_by_id(self, element_id):
#         return self.browser.wait.until(EC.element_to_be_clickable(
#             (By.ID, element_id)))
#
#     def user_login(self):
#         import json
#         with open("taskbuster/fixtures/twitter_user.json") as f:
#             credentials = json.loads(f.read())
#         for key, value in credentials.items():
#             self.get_element_by_id(key).send_keys(value)
#         for btn in ["allow"]:
#             self.get_button_by_id(btn).click()
#         return
#
#     def get_full_url(self, namespace):
#         return self.live_server_url + reverse(namespace)
#
#     def test_twitter_login(self):
#         self.browser.get(self.get_full_url("home"))
#         twitter_login = self.get_element_by_id("twitter_login")
#         with self.assertRaises(TimeoutException):
#             self.get_element_by_id("logout")
#         self.assertEqual(
#             twitter_login.get_attribute("href"),
#             self.live_server_url + "/accounts/twitter/login")
#         twitter_login.click()
#         self.user_login()
#         with self.assertRaises(TimeoutException):
#             self.get_element_by_id("twitter_login")
#         logout = self.get_element_by_id("logout")
#         logout.click()
#         twitter_login = self.get_element_by_id("twitter_login")