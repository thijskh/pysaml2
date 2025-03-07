#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
from saml2.xmldsig import SIG_RSA_SHA256
from saml2 import sigver
from saml2 import extension_elements_to_elements
from saml2 import class_name
from saml2 import time_util
from saml2 import saml, samlp
from saml2 import config
from saml2.cert import read_cert_from_file
from saml2.cert import CertificateError
from saml2.sigver import pre_encryption_part
from saml2.sigver import make_temp
from saml2.sigver import XmlsecError
from saml2.mdstore import MetadataStore
from saml2.saml import assertion_from_string
from saml2.saml import EncryptedAssertion
from saml2.samlp import response_from_string
from saml2.s_utils import factory
from saml2.s_utils import do_attribute_statement
from saml2.s_utils import success_status_factory

import pytest
from pytest import raises

from pathutils import full_path


SIGNED = full_path("saml_signed.xml")
UNSIGNED = full_path("saml_unsigned.xml")
SIMPLE_SAML_PHP_RESPONSE = full_path("simplesamlphp_authnresponse.xml")
OKTA_RESPONSE = full_path("okta_response.xml")
OKTA_ASSERTION = full_path("okta_assertion")

PUB_KEY = full_path("test.pem")
PRIV_KEY = full_path("test.key")

ENC_PUB_KEY = full_path("pki/test_1.crt")
ENC_PRIV_KEY = full_path("pki/test.key")

INVALID_KEY = full_path("non-existent.key")

IDP_EXAMPLE = full_path("idp_example.xml")
METADATA_CERT = full_path("metadata_cert.xml")


def _eq(l1, l2):
    return set(l1) == set(l2)


CERT1 = """MIICsDCCAhmgAwIBAgIJAJrzqSSwmDY9MA0GCSqGSIb3DQEBBQUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIEwpTb21lLVN0YXRlMSEwHwYDVQQKExhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMDkxMDA2MTk0OTQxWhcNMDkxMTA1MTk0OTQxWjBF
MQswCQYDVQQGEwJBVTETMBEGA1UECBMKU29tZS1TdGF0ZTEhMB8GA1UEChMYSW50
ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKB
gQDJg2cms7MqjniT8Fi/XkNHZNPbNVQyMUMXE9tXOdqwYCA1cc8vQdzkihscQMXy
3iPw2cMggBu6gjMTOSOxECkuvX5ZCclKr8pXAJM5cY6gVOaVO2PdTZcvDBKGbiaN
efiEw5hnoZomqZGp8wHNLAUkwtH9vjqqvxyS/vclc6k2ewIDAQABo4GnMIGkMB0G
A1UdDgQWBBRePsKHKYJsiojE78ZWXccK9K4aJTB1BgNVHSMEbjBsgBRePsKHKYJs
iojE78ZWXccK9K4aJaFJpEcwRTELMAkGA1UEBhMCQVUxEzARBgNVBAgTClNvbWUt
U3RhdGUxITAfBgNVBAoTGEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZIIJAJrzqSSw
mDY9MAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQEFBQADgYEAJSrKOEzHO7TL5cy6
h3qh+3+JAk8HbGBW+cbX6KBCAw/mzU8flK25vnWwXS3dv2FF3Aod0/S7AWNfKib5
U/SA9nJaz/mWeF9S0farz9AQFc8/NSzAzaVq7YbM4F6f6N2FRl7GikdXRCed45j6
mrPzGzk3ECbupFnqyREH3+ZPSdk="""

CERT_SSP = """MIICizCCAfQCCQCY8tKaMc0BMjANBgkqhkiG9w0BAQUFADCBiTELMAkGA1UEBhMC
Tk8xEjAQBgNVBAgTCVRyb25kaGVpbTEQMA4GA1UEChMHVU5JTkVUVDEOMAwGA1UE
CxMFRmVpZGUxGTAXBgNVBAMTEG9wZW5pZHAuZmVpZGUubm8xKTAnBgkqhkiG9w0B
CQEWGmFuZHJlYXMuc29sYmVyZ0B1bmluZXR0Lm5vMB4XDTA4MDUwODA5MjI0OFoX
DTM1MDkyMzA5MjI0OFowgYkxCzAJBgNVBAYTAk5PMRIwEAYDVQQIEwlUcm9uZGhl
aW0xEDAOBgNVBAoTB1VOSU5FVFQxDjAMBgNVBAsTBUZlaWRlMRkwFwYDVQQDExBv
cGVuaWRwLmZlaWRlLm5vMSkwJwYJKoZIhvcNAQkBFhphbmRyZWFzLnNvbGJlcmdA
dW5pbmV0dC5ubzCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAt8jLoqI1VTlx
AZ2axiDIThWcAOXdu8KkVUWaN/SooO9O0QQ7KRUjSGKN9JK65AFRDXQkWPAu4Hln
O4noYlFSLnYyDxI66LCr71x4lgFJjqLeAvB/GqBqFfIZ3YK/NrhnUqFwZu63nLrZ
jcUZxNaPjOOSRSDaXpv1kb5k3jOiSGECAwEAATANBgkqhkiG9w0BAQUFAAOBgQBQ
Yj4cAafWaYfjBU2zi1ElwStIaJ5nyp/s/8B8SAPK2T79McMyccP3wSW13LHkmM1j
wKe3ACFXBvqGQN0IbcH49hu0FKhYFM/GPDJcIHFBsiyMBXChpye9vBaTNEBCtU3K
jjyG0hRT2mAQ9h+bkPmOvlEo/aH0xR68Z9hw4PF13w=="""

try:
    from pyasn1.codec.der import decoder
except ImportError:
    decoder = None


def test_cert_from_instance_1():
    with open(SIGNED) as fp:
        xml_response = fp.read()
    response = samlp.response_from_string(xml_response)
    assertion = response.assertion[0]
    certs = sigver.cert_from_instance(assertion)
    assert len(certs) == 1
    print(certs[0])
    assert certs[0] == CERT1


@pytest.mark.skipif(not decoder, reason="pyasn1 is not installed")
def test_cert_from_instance_ssp():
    with open(SIMPLE_SAML_PHP_RESPONSE) as fp:
        xml_response = fp.read()
    response = samlp.response_from_string(xml_response)
    assertion = response.assertion[0]
    certs = sigver.cert_from_instance(assertion)
    assert len(certs) == 1
    assert certs[0] == CERT_SSP
    der = base64.b64decode(certs[0])
    print(str(decoder.decode(der)).replace('.', "\n."))
    assert decoder.decode(der)


class FakeConfig():
    """
    Configuration parameters for signature validation test cases.
    """
    xmlsec_binary = None
    crypto_backend = 'xmlsec1'
    only_use_keys_in_metadata = False
    metadata = None
    cert_file = PUB_KEY
    key_file = PRIV_KEY
    encryption_keypairs = [{"key_file": ENC_PRIV_KEY, "cert_file": ENC_PUB_KEY}]
    enc_key_files = [ENC_PRIV_KEY]
    cert_handler_extra_class = None
    generate_cert_func = None
    generate_cert_info = False
    tmp_cert_file = None
    tmp_key_file = None
    validate_certificate = False
    delete_tmpfiles = True

    def getattr(self, attr, default):
        return getattr(self, attr, default)


class TestSecurity():
    def setup_class(self):
        # This would be one way to initialize the security context :
        #
        #    conf = config.SPConfig()
        #    conf.load_file("server_conf")
        #    conf.only_use_keys_in_metadata = False
        #
        # but instead, FakeConfig() is used to really only use the minimal
        # set of parameters needed for these test cases. Other test cases
        # (TestSecurityMetadata below) excersise the SPConfig() mechanism.
        #
        conf = FakeConfig()
        self.sec = sigver.security_context(conf)

        self._assertion = factory(
            saml.Assertion,
            version="2.0",
            id="id-11111",
            issuer=saml.Issuer(text="the-issuer"),
            issue_instant="2009-10-30T13:20:28Z",
            signature=sigver.pre_signature_part("id-11111", self.sec.my_cert, 1),
            attribute_statement=do_attribute_statement({
                ("name:surName", "nameformat", "surName"): ("Foo", ""),
                ("name:givenName", "nameformat", "givenName"): ("Bar", ""),
            })
        )

    def test_verify_1(self):
        with open(SIGNED) as fp:
            xml_response = fp.read()
        response = self.sec.correctly_signed_response(xml_response)
        assert response

    def test_non_verify_1(self):
        """ unsigned is OK """
        with open(UNSIGNED) as fp:
            xml_response = fp.read()
        response = self.sec.correctly_signed_response(xml_response)
        assert response

    def test_sign_assertion(self):
        ass = self._assertion
        print(ass)
        sign_ass = self.sec.sign_assertion("%s" % ass, node_id=ass.id)
        #print(sign_ass)
        sass = saml.assertion_from_string(sign_ass)
        #print(sass)
        assert _eq(sass.keyswv(), ['issuer', 'attribute_statement', 'issue_instant',
                                   'version', 'signature', 'id'])
        assert sass.version == "2.0"
        assert sass.id == "id-11111"
        assert time_util.str_to_time(sass.issue_instant)

        print("Crypto version : %s" % (self.sec.crypto.version()))

        item = self.sec.check_signature(sass, class_name(sass), sign_ass)

        assert isinstance(item, saml.Assertion)

    def test_multiple_signatures_assertion(self):
        ass = self._assertion
        # basic test with two of the same
        to_sign = [(ass, ass.id), (ass, ass.id)]
        sign_ass = self.sec.multiple_signatures(str(ass), to_sign)
        sass = saml.assertion_from_string(sign_ass)
        assert _eq(sass.keyswv(), ['issuer', 'attribute_statement', 'issue_instant',
                                   'version', 'signature', 'id'])
        assert sass.version == "2.0"
        assert sass.id == "id-11111"
        assert time_util.str_to_time(sass.issue_instant)

        print("Crypto version : %s" % (self.sec.crypto.version()))

        item = self.sec.check_signature(sass, class_name(sass),
                                        sign_ass, must=True)

        assert isinstance(item, saml.Assertion)

    def test_multiple_signatures_response(self):
        response = factory(
            samlp.Response,
            issuer=saml.Issuer(text="the-isser"),
            status=success_status_factory(),
            assertion=self._assertion,
            version="2.0",
            issue_instant="2099-10-30T13:20:28Z",
            id="id-22222",
            signature=sigver.pre_signature_part(
                "id-22222", self.sec.my_cert
            ),
        )

        # order is important, we can't validate if the signatures are made
        # in the reverse order
        to_sign = [(self._assertion, self._assertion.id), (response, response.id)]
        s_response = self.sec.multiple_signatures(str(response), to_sign)
        assert s_response is not None
        response = response_from_string(s_response)

        item = self.sec.check_signature(response, class_name(response), s_response, must=True)
        assert item == response
        assert item.id == "id-22222"

        s_assertion = item.assertion[0]
        assert isinstance(s_assertion, saml.Assertion)
        # make sure the assertion was modified when we supposedly signed it
        assert s_assertion != self._assertion

        ci = "".join(sigver.cert_from_instance(s_assertion)[0].split())
        assert ci == self.sec.my_cert

        res = self.sec.check_signature(s_assertion, class_name(s_assertion),
                                       s_response, must=True)
        assert res == s_assertion
        assert s_assertion.id == "id-11111"
        assert s_assertion.version == "2.0"
        assert _eq(s_assertion.keyswv(), ['issuer', 'attribute_statement',
                                          'issue_instant',
                                          'version', 'signature', 'id'])

    def test_sign_response(self):
        response = factory(
            samlp.Response,
            issuer=saml.Issuer(text="the-isser"),
            status=success_status_factory(),
            assertion=self._assertion,
            version="2.0",
            issue_instant="2099-10-30T13:20:28Z",
            id="id-22222",
            signature=sigver.pre_signature_part(
                "id-22222", self.sec.my_cert
            ),
        )

        to_sign = [(class_name(self._assertion), self._assertion.id),
                   (class_name(response), response.id)]
        s_response = sigver.signed_instance_factory(response, self.sec, to_sign)

        assert s_response is not None
        print(s_response)
        response = response_from_string(s_response)
        sass = response.assertion[0]

        print(sass)
        assert _eq(sass.keyswv(), ['issuer', 'attribute_statement', 'issue_instant',
                                   'version', 'signature', 'id'])
        assert sass.version == "2.0"
        assert sass.id == "id-11111"

        item = self.sec.check_signature(response, class_name(response),
                                        s_response)
        assert isinstance(item, samlp.Response)
        assert item.id == "id-22222"

    def test_sign_response_2(self):
        assertion2 = factory(
            saml.Assertion,
            version="2.0",
            id="id-11122",
            issuer=saml.Issuer(text="the-issuer-2"),
            issue_instant="2009-10-30T13:20:28Z",
            signature=sigver.pre_signature_part("id-11122", self.sec .my_cert),
            attribute_statement=do_attribute_statement({
                ("name:surName", "nameformat", "surName"): ("Fox", ""),
                ("name:givenName", "nameformat", "givenName"): ("Bear", ""),
            })
        )
        response = factory(
            samlp.Response,
            issuer=saml.Issuer(text="the-isser-2"),
            status=success_status_factory(),
            assertion=assertion2,
            version="2.0",
            issue_instant="2099-10-30T13:20:28Z",
            id="id-22233",
            signature=sigver.pre_signature_part("id-22233", self.sec.my_cert),
        )


        to_sign = [(class_name(assertion2), assertion2.id),
                   (class_name(response), response.id)]

        s_response = sigver.signed_instance_factory(response, self.sec, to_sign)

        assert s_response is not None
        response2 = response_from_string(s_response)

        sass = response2.assertion[0]
        ['signature', 'attribute_statement', 'version', 'id', 'issue_instant']
        ['issuer', 'attribute_statement', 'issue_instant', 'version', 'signature', 'id']

        assert _eq(sass.keyswv(), ['issuer', 'attribute_statement', 'issue_instant',
                                   'version', 'signature', 'id'])
        assert sass.version == "2.0"
        assert sass.id == "id-11122"

        item = self.sec.check_signature(response2, class_name(response), s_response)

        assert isinstance(item, samlp.Response)

    def test_sign_verify(self):
        response = factory(samlp.Response,
                           assertion=self._assertion,
                           id="id-22233",
                           signature=sigver.pre_signature_part("id-22233",
                                                               self.sec
                                                               .my_cert))

        to_sign = [(class_name(self._assertion), self._assertion.id),
                   (class_name(response), response.id)]

        s_response = sigver.signed_instance_factory(response, self.sec,
                                                    to_sign)

        print(s_response)
        res = self.sec.verify_signature(s_response,
                                        node_name=class_name(samlp.Response()))

        print(res)
        assert res

    def test_sign_verify_with_cert_from_instance(self):
        response = factory(
            samlp.Response,
            issuer=saml.Issuer(text="the-isser"),
            status=success_status_factory(),
            assertion=self._assertion,
            version="2.0",
            issue_instant="2099-10-30T13:20:28Z",
            id="id-22222",
            signature=sigver.pre_signature_part(
                "id-22222", self.sec.my_cert
            ),
        )

        to_sign = [(class_name(self._assertion), self._assertion.id),
                   (class_name(response), response.id)]

        s_response = sigver.signed_instance_factory(response, self.sec, to_sign)

        response2 = response_from_string(s_response)

        ci = "".join(sigver.cert_from_instance(response2)[0].split())

        assert ci == self.sec.my_cert

        res = self.sec.verify_signature(s_response,
                                        node_name=class_name(samlp.Response()))

        assert res

        res = self.sec._check_signature(s_response, response2,
                                        class_name(response2), s_response)
        assert res == response2

    def test_sign_verify_assertion_with_cert_from_instance(self):
        assertion = factory(
            saml.Assertion,
            version="2.0",
            id="id-11100",
            issuer=saml.Issuer(text="the-issuer"),
            issue_instant="2009-10-30T13:20:28Z",
            signature=sigver.pre_signature_part("id-11100", self.sec .my_cert),
            attribute_statement=do_attribute_statement({
                ("name:surName", "nameformat", "surName"): ("Fox", ""),
                ("name:givenName", "nameformat", "givenName"): ("Bear", ""),
            })
        )

        to_sign = [(class_name(assertion), assertion.id)]
        s_assertion = sigver.signed_instance_factory(assertion, self.sec,
                                                     to_sign)
        print(s_assertion)
        ass = assertion_from_string(s_assertion)
        ci = "".join(sigver.cert_from_instance(ass)[0].split())
        assert ci == self.sec.my_cert

        res = self.sec.verify_signature(s_assertion,
                                        node_name=class_name(ass))
        assert res

        res = self.sec._check_signature(s_assertion, ass, class_name(ass))

        assert res

    def test_exception_sign_verify_with_cert_from_instance(self):
        assertion = factory(
            saml.Assertion,
            version="2.0",
            id="id-11100",
            issuer=saml.Issuer(text="the-issuer-2"),
            issue_instant="2009-10-30T13:20:28Z",
            attribute_statement=do_attribute_statement({
                ("name:surName", "nameformat", "surName"): ("Foo", ""),
                ("name:givenName", "nameformat", "givenName"): ("Bar", ""),
            })
        )

        response = factory(
            samlp.Response,
            issuer=saml.Issuer(text="the-isser"),
            status=success_status_factory(),
            assertion=assertion,
            version="2.0",
            issue_instant="2099-10-30T13:20:28Z",
            id="id-22222",
            signature=sigver.pre_signature_part(
                "id-22222", self.sec.my_cert
            ),
        )


        to_sign = [(class_name(response), response.id)]

        s_response = sigver.signed_instance_factory(response, self.sec, to_sign)

        response2 = response_from_string(s_response)
        # Change something that should make everything fail
        response2.id = "id-23456"
        with raises(sigver.SignatureError):
            self.sec._check_signature(s_response, response2, class_name(response2))


class TestSecurityNonAsciiAva():
    def setup_class(self):
        # This would be one way to initialize the security context :
        #
        #    conf = config.SPConfig()
        #    conf.load_file("server_conf")
        #    conf.only_use_keys_in_metadata = False
        #
        # but instead, FakeConfig() is used to really only use the minimal
        # set of parameters needed for these test cases. Other test cases
        # (TestSecurityMetadata below) excersise the SPConfig() mechanism.
        #
        conf = FakeConfig()
        self.sec = sigver.security_context(conf)

        self._assertion = factory(
            saml.Assertion,
            version="2.0",
            id="id-11111",
            issuer=saml.Issuer(text="the-issuer"),
            issue_instant="2009-10-30T13:20:28Z",
            signature=sigver.pre_signature_part("id-11111", self.sec.my_cert, 1),
            attribute_statement=do_attribute_statement({
                ("name:surName", "nameformat", "surName"): ("Föö", ""),
                ("name:givenName", "nameformat", "givenName"): ("Bär", ""),
            })
        )

    def test_verify_1(self):
        with open(SIGNED) as fp:
            xml_response = fp.read()
        response = self.sec.correctly_signed_response(xml_response)
        assert response

    def test_non_verify_1(self):
        """ unsigned is OK """
        with open(UNSIGNED) as fp:
            xml_response = fp.read()
        response = self.sec.correctly_signed_response(xml_response)
        assert response

    def test_sign_assertion(self):
        ass = self._assertion
        print(ass)
        sign_ass = self.sec.sign_assertion("%s" % ass, node_id=ass.id)
        #print(sign_ass)
        sass = saml.assertion_from_string(sign_ass)
        #print(sass)

        assert _eq(sass.keyswv(), ['issuer', 'attribute_statement', 'issue_instant',
                                   'version', 'signature', 'id'])
        assert sass.version == "2.0"
        assert sass.id == "id-11111"
        assert time_util.str_to_time(sass.issue_instant)

        print("Crypto version : %s" % (self.sec.crypto.version()))

        item = self.sec.check_signature(sass, class_name(sass), sign_ass)

        assert isinstance(item, saml.Assertion)

    def test_multiple_signatures_assertion(self):
        ass = self._assertion
        # basic test with two of the same
        to_sign = [(ass, ass.id), (ass, ass.id)]
        sign_ass = self.sec.multiple_signatures(str(ass), to_sign)
        sass = saml.assertion_from_string(sign_ass)
        assert _eq(sass.keyswv(), ['issuer', 'attribute_statement', 'issue_instant',
                                   'version', 'signature', 'id'])
        assert sass.version == "2.0"
        assert sass.id == "id-11111"
        assert time_util.str_to_time(sass.issue_instant)

        print("Crypto version : %s" % (self.sec.crypto.version()))

        item = self.sec.check_signature(sass, class_name(sass),
                                        sign_ass, must=True)

        assert isinstance(item, saml.Assertion)

    def test_multiple_signatures_response(self):
        response = factory(
            samlp.Response,
            issuer=saml.Issuer(text="the-isser"),
            status=success_status_factory(),
            assertion=self._assertion,
            version="2.0",
            issue_instant="2099-10-30T13:20:28Z",
            id="id-22222",
            signature=sigver.pre_signature_part(
                "id-22222", self.sec.my_cert
            ),
        )

        # order is important, we can't validate if the signatures are made
        # in the reverse order
        to_sign = [(self._assertion, self._assertion.id), (response, response.id)]
        s_response = self.sec.multiple_signatures(str(response), to_sign)
        assert s_response is not None
        response = response_from_string(s_response)

        item = self.sec.check_signature(response, class_name(response),
                                        s_response, must=True)
        assert item == response
        assert item.id == "id-22222"

        s_assertion = item.assertion[0]
        assert isinstance(s_assertion, saml.Assertion)
        # make sure the assertion was modified when we supposedly signed it
        assert s_assertion != self._assertion

        ci = "".join(sigver.cert_from_instance(s_assertion)[0].split())
        assert ci == self.sec.my_cert

        res = self.sec.check_signature(s_assertion, class_name(s_assertion),
                                       s_response, must=True)
        assert res == s_assertion
        assert s_assertion.id == "id-11111"
        assert s_assertion.version == "2.0"
        assert _eq(s_assertion.keyswv(), ['issuer', 'attribute_statement',
                                          'issue_instant',
                                          'version', 'signature', 'id'])

    def test_sign_response(self):
        response = factory(
            samlp.Response,
            issuer=saml.Issuer(text="the-isser"),
            status=success_status_factory(),
            assertion=self._assertion,
            version="2.0",
            issue_instant="2099-10-30T13:20:28Z",
            id="id-22222",
            signature=sigver.pre_signature_part(
                "id-22222", self.sec.my_cert
            ),
        )

        to_sign = [(class_name(self._assertion), self._assertion.id),
                   (class_name(response), response.id)]
        s_response = sigver.signed_instance_factory(response, self.sec, to_sign)

        assert s_response is not None
        print(s_response)
        response = response_from_string(s_response)
        sass = response.assertion[0]

        print(sass)
        assert _eq(sass.keyswv(), ['issuer', 'attribute_statement', 'issue_instant',
                                   'version', 'signature', 'id'])
        assert sass.version == "2.0"
        assert sass.id == "id-11111"

        item = self.sec.check_signature(response, class_name(response), s_response)
        assert isinstance(item, samlp.Response)
        assert item.id == "id-22222"

    def test_sign_response_2(self):
        assertion2 = factory(
            saml.Assertion,
            version="2.0",
            id="id-11122",
            issuer=saml.Issuer(text="the-issuer-2"),
            issue_instant="2009-10-30T13:20:28Z",
            signature=sigver.pre_signature_part("id-11122", self.sec .my_cert),
            attribute_statement=do_attribute_statement({
                ("name:surName", "nameformat", "surName"): ("Räv", ""),
                ("name:givenName", "nameformat", "givenName"): ("Björn", ""),
            })
        )
        response = factory(
            samlp.Response,
            issuer=saml.Issuer(text="the-isser"),
            status=success_status_factory(),
            assertion=assertion2,
            version="2.0",
            issue_instant="2099-10-30T13:20:28Z",
            id="id-22233",
            signature=sigver.pre_signature_part("id-22233", self.sec.my_cert),
        )

        to_sign = [(class_name(assertion2), assertion2.id),
                   (class_name(response), response.id)]

        s_response = sigver.signed_instance_factory(response, self.sec, to_sign)

        assert s_response is not None
        response2 = response_from_string(s_response)

        sass = response2.assertion[0]
        assert _eq(sass.keyswv(), ['issuer', 'attribute_statement', 'issue_instant',
                                   'version', 'signature', 'id'])
        assert sass.version == "2.0"
        assert sass.id == "id-11122"

        item = self.sec.check_signature(response2, class_name(response),
                                        s_response)

        assert isinstance(item, samlp.Response)

    def test_sign_verify(self):
        response = factory(
            samlp.Response,
            issuer=saml.Issuer(text="the-isser"),
            status=success_status_factory(),
            assertion=self._assertion,
            version="2.0",
            issue_instant="2099-10-30T13:20:28Z",
            id="id-22233",
            signature=sigver.pre_signature_part(
                "id-22233", self.sec.my_cert
            ),
        )

        to_sign = [(class_name(self._assertion), self._assertion.id),
                   (class_name(response), response.id)]

        s_response = sigver.signed_instance_factory(response, self.sec,
                                                    to_sign)

        print(s_response)
        res = self.sec.verify_signature(s_response,
                                        node_name=class_name(samlp.Response()))

        print(res)
        assert res

    def test_sign_verify_with_cert_from_instance(self):
        response = factory(
            samlp.Response,
            issuer=saml.Issuer(text="the-isser"),
            status=success_status_factory(),
            assertion=self._assertion,
            version="2.0",
            issue_instant="2099-10-30T13:20:28Z",
            id="id-22222",
            signature=sigver.pre_signature_part(
                "id-22222", self.sec.my_cert
            ),
        )

        to_sign = [(class_name(self._assertion), self._assertion.id),
                   (class_name(response), response.id)]

        s_response = sigver.signed_instance_factory(response, self.sec, to_sign)

        response2 = response_from_string(s_response)

        ci = "".join(sigver.cert_from_instance(response2)[0].split())

        assert ci == self.sec.my_cert

        res = self.sec.verify_signature(s_response,
                                        node_name=class_name(samlp.Response()))

        assert res

        res = self.sec._check_signature(s_response, response2,
                                        class_name(response2), s_response)
        assert res == response2

    def test_sign_verify_assertion_with_cert_from_instance(self):
        assertion = factory(
            saml.Assertion,
            version="2.0",
            id="id-11100",
            issuer=saml.Issuer(text="the-issuer"),
            issue_instant="2009-10-30T13:20:28Z",
            signature=sigver.pre_signature_part("id-11100", self.sec.my_cert, 1),
            attribute_statement=do_attribute_statement({
                ("name:surName", "nameformat", "surName"): ("Räv", ""),
                ("name:givenName", "nameformat", "givenName"): ("Björn", ""),
            })
        )

        to_sign = [(class_name(assertion), assertion.id)]
        s_assertion = sigver.signed_instance_factory(assertion, self.sec,
                                                     to_sign)
        print(s_assertion)
        ass = assertion_from_string(s_assertion)
        ci = "".join(sigver.cert_from_instance(ass)[0].split())
        assert ci == self.sec.my_cert

        res = self.sec.verify_signature(s_assertion,
                                        node_name=class_name(ass))
        assert res

        res = self.sec._check_signature(s_assertion, ass, class_name(ass))

        assert res

    def test_exception_sign_verify_with_cert_from_instance(self):
        assertion = factory(
            saml.Assertion,
            version="2.0",
            id="id-11100",
            issuer=saml.Issuer(text="the-issuer"),
            issue_instant="2009-10-30T13:20:28Z",
            attribute_statement=do_attribute_statement({
                ("name:surName", "nameformat", "surName"): ("Föö", ""),
                ("name:givenName", "nameformat", "givenName"): ("Bär", ""),
            })
        )

        response = factory(
            samlp.Response,
            issuer=saml.Issuer(text="the-isser"),
            status=success_status_factory(),
            assertion=assertion,
            version="2.0",
            issue_instant="2099-10-30T13:20:28Z",
            id="id-22222",
            signature=sigver.pre_signature_part(
                "id-22222", self.sec.my_cert
            ),
        )

        to_sign = [(class_name(response), response.id)]

        s_response = sigver.signed_instance_factory(response, self.sec, to_sign)

        response2 = response_from_string(s_response)
        # Change something that should make everything fail
        response2.id = "id-23456"
        with raises(sigver.SignatureError):
            self.sec._check_signature(s_response, response2, class_name(response2))


class TestSecurityMetadata():
    def setup_class(self):
        conf = config.SPConfig()
        conf.load_file("server_conf")
        md = MetadataStore([saml, samlp], None, conf)
        md.load("local", METADATA_CERT)

        conf.metadata = md
        conf.only_use_keys_in_metadata = False
        self.sec = sigver.security_context(conf)

        assertion = factory(
            saml.Assertion,
            version="2.0",
            id="id-11111",
            issuer=saml.Issuer(text="the-issuer"),
            issue_instant="2009-10-30T13:20:28Z",
            signature=sigver.pre_signature_part("id-11111", self.sec.my_cert, 1),
            attribute_statement=do_attribute_statement({
                ("name:surName", "nameformat", "surName"): ("Foo", ""),
                ("name:givenName", "nameformat", "givenName"): ("Bar", ""),
            })
        )

        assertion = factory(
            saml.Assertion, version="2.0", id="id-11111",
            issue_instant="2009-10-30T13:20:28Z",
            signature=sigver.pre_signature_part("id-11111", self.sec.my_cert, 1),
            attribute_statement=do_attribute_statement(
                {("", "", "surName"): ("Foo", ""),
                 ("", "", "givenName"): ("Bar", ""), })
        )


class TestSecurityMetadataNonAsciiAva():
    def setup_class(self):
        conf = config.SPConfig()
        conf.load_file("server_conf")
        md = MetadataStore([saml, samlp], None, conf)
        md.load("local", METADATA_CERT)

        conf.metadata = md
        conf.only_use_keys_in_metadata = False
        self.sec = sigver.security_context(conf)

        assertion = factory(
            saml.Assertion, version="2.0", id="id-11111",
            issue_instant="2009-10-30T13:20:28Z",
            signature=sigver.pre_signature_part("id-11111", self.sec.my_cert, 1),
            attribute_statement=do_attribute_statement(
                {("", "", "surName"): ("Föö", ""),
                 ("", "", "givenName"): ("Bär", ""), })
        )


def test_xbox():
    conf = config.SPConfig()
    conf.load_file("server_conf")
    md = MetadataStore([saml, samlp], None, conf)
    md.load("local", IDP_EXAMPLE)

    conf.metadata = md
    conf.only_use_keys_in_metadata = False
    sec = sigver.security_context(conf)

    assertion = factory(
        saml.Assertion, version="2.0", id="id-11111",
        issue_instant="2009-10-30T13:20:28Z",
        signature=sigver.pre_signature_part("id-11111", sec.my_cert, 1),
        attribute_statement=do_attribute_statement(
            {
                ("", "", "surName"): ("Foo", ""),
                ("", "", "givenName"): ("Bar", ""),
            }
        )
    )

    sigass = sec.sign_statement(
        assertion,
        class_name(assertion),
        key_file=PRIV_KEY,
        node_id=assertion.id,
    )

    _ass0 = saml.assertion_from_string(sigass)
    encrypted_assertion = EncryptedAssertion()
    encrypted_assertion.add_extension_element(_ass0)

    tmp = make_temp(
        str(pre_encryption_part()).encode('utf-8'), decode=False
    )
    enctext = sec.crypto.encrypt(
        str(encrypted_assertion),
        conf.cert_file,
        tmp.name,
        "des-192",
        '/*[local-name()="EncryptedAssertion"]/*[local-name()="Assertion"]',
    )

    decr_text = sec.decrypt(enctext, key_file=PRIV_KEY)
    _seass = saml.encrypted_assertion_from_string(decr_text)
    assertions = []
    assers = extension_elements_to_elements(
        _seass.extension_elements, [saml, samlp]
    )

    for ass in assers:
        _txt = sec.verify_signature(
            str(ass), PUB_KEY, node_name=class_name(assertion)
        )
        if _txt:
            assertions.append(ass)

    assert assertions
    print(assertions)


def test_xbox_non_ascii_ava():
    conf = config.SPConfig()
    conf.load_file("server_conf")
    md = MetadataStore([saml, samlp], None, conf)
    md.load("local", IDP_EXAMPLE)

    conf.metadata = md
    conf.only_use_keys_in_metadata = False
    sec = sigver.security_context(conf)

    assertion = factory(
        saml.Assertion, version="2.0", id="id-11111",
        issue_instant="2009-10-30T13:20:28Z",
        signature=sigver.pre_signature_part("id-11111", sec.my_cert, 1),
        attribute_statement=do_attribute_statement(
            {
                ("", "", "surName"): ("Föö", ""),
                ("", "", "givenName"): ("Bär", ""),
            }
        )
    )

    sigass = sec.sign_statement(
        assertion,
        class_name(assertion),
        key_file=PRIV_KEY,
        node_id=assertion.id,
    )

    _ass0 = saml.assertion_from_string(sigass)
    encrypted_assertion = EncryptedAssertion()
    encrypted_assertion.add_extension_element(_ass0)

    tmp = make_temp(
        str(pre_encryption_part()).encode('utf-8'), decode=False
    )
    enctext = sec.crypto.encrypt(
        str(encrypted_assertion),
        conf.cert_file,
        tmp.name,
        "des-192",
        '/*[local-name()="EncryptedAssertion"]/*[local-name()="Assertion"]',
    )

    decr_text = sec.decrypt(enctext, key_file=PRIV_KEY)
    _seass = saml.encrypted_assertion_from_string(decr_text)
    assertions = []
    assers = extension_elements_to_elements(
        _seass.extension_elements, [saml, samlp]
    )

    for ass in assers:
        _txt = sec.verify_signature(
            str(ass), PUB_KEY, node_name=class_name(assertion)
        )
        if _txt:
            assertions.append(ass)

    assert assertions
    print(assertions)


def test_okta():
    conf = config.Config()
    conf.load_file("server_conf")
    conf.id_attr_name = 'Id'
    md = MetadataStore([saml, samlp], None, conf)
    md.load("local", IDP_EXAMPLE)

    conf.metadata = md
    conf.only_use_keys_in_metadata = False
    sec = sigver.security_context(conf)
    with open(OKTA_RESPONSE) as f:
        enctext = f.read()
    decr_text = sec.decrypt(enctext)
    _seass = saml.encrypted_assertion_from_string(decr_text)
    assers = extension_elements_to_elements(_seass.extension_elements,
                                            [saml, samlp])

    with open(OKTA_ASSERTION) as f:
        okta_assertion = f.read()
    expected_assert = assertion_from_string(okta_assertion)
    assert len(assers) == 1
    assert assers[0] == expected_assert


def test_xmlsec_err():
    conf = config.SPConfig()
    conf.load_file("server_conf")
    md = MetadataStore([saml, samlp], None, conf)
    md.load("local", IDP_EXAMPLE)

    conf.metadata = md
    conf.only_use_keys_in_metadata = False
    sec = sigver.security_context(conf)

    assertion = factory(
        saml.Assertion, version="2.0", id="id-11111",
        issue_instant="2009-10-30T13:20:28Z",
        signature=sigver.pre_signature_part("id-11111", sec.my_cert, 1),
        attribute_statement=do_attribute_statement(
            {("", "", "surName"): ("Foo", ""),
             ("", "", "givenName"): ("Bar", ""), })
    )

    with raises(XmlsecError):
        sec.sign_statement(
            assertion,
            class_name(assertion),
            key_file=INVALID_KEY,
            node_id=assertion.id,
        )


def test_xmlsec_err_non_ascii_ava():
    conf = config.SPConfig()
    conf.load_file("server_conf")
    md = MetadataStore([saml, samlp], None, conf)
    md.load("local", IDP_EXAMPLE)

    conf.metadata = md
    conf.only_use_keys_in_metadata = False
    sec = sigver.security_context(conf)

    assertion = factory(
        saml.Assertion, version="2.0", id="id-11111",
        issue_instant="2009-10-30T13:20:28Z",
        signature=sigver.pre_signature_part("id-11111", sec.my_cert, 1),
        attribute_statement=do_attribute_statement(
            {("", "", "surName"): ("Föö", ""),
             ("", "", "givenName"): ("Bär", ""), })
    )

    with raises(XmlsecError):
        sec.sign_statement(
            assertion,
            class_name(assertion),
            key_file=INVALID_KEY,
            node_id=assertion.id,
        )


def test_sha256_signing():
    conf = config.SPConfig()
    conf.load_file("server_conf")
    md = MetadataStore([saml, samlp], None, conf)
    md.load("local", IDP_EXAMPLE)

    conf.metadata = md
    conf.only_use_keys_in_metadata = False
    sec = sigver.security_context(conf)

    assertion = factory(
        saml.Assertion, version="2.0", id="id-11111",
        issue_instant="2009-10-30T13:20:28Z",
        signature=sigver.pre_signature_part("id-11111", sec.my_cert, 1,
                                            sign_alg=SIG_RSA_SHA256),
        attribute_statement=do_attribute_statement(
            {("", "", "surName"): ("Foo", ""),
             ("", "", "givenName"): ("Bar", ""), })
    )

    s = sec.sign_statement(assertion, class_name(assertion),
                           key_file=PRIV_KEY,
                           node_id=assertion.id)
    assert s


def test_sha256_signing_non_ascii_ava():
    conf = config.SPConfig()
    conf.load_file("server_conf")
    md = MetadataStore([saml, samlp], None, conf)
    md.load("local", IDP_EXAMPLE)

    conf.metadata = md
    conf.only_use_keys_in_metadata = False
    sec = sigver.security_context(conf)

    assertion = factory(
        saml.Assertion, version="2.0", id="id-11111",
        issue_instant="2009-10-30T13:20:28Z",
        signature=sigver.pre_signature_part("id-11111", sec.my_cert, 1,
                                            sign_alg=SIG_RSA_SHA256),
        attribute_statement=do_attribute_statement(
            {("", "", "surName"): ("Föö", ""),
             ("", "", "givenName"): ("Bär", ""), })
    )

    s = sec.sign_statement(assertion, class_name(assertion),
                           key_file=PRIV_KEY,
                           node_id=assertion.id)
    assert s


def test_xmlsec_output_line_parsing():
    output1 = "prefix\nOK\npostfix"
    assert sigver.parse_xmlsec_output(output1)

    output2 = "prefix\nFAIL\npostfix"
    with raises(sigver.XmlsecError):
        sigver.parse_xmlsec_output(output2)

    output3 = "prefix\r\nOK\r\npostfix"
    assert sigver.parse_xmlsec_output(output3)

    output4 = "prefix\r\nFAIL\r\npostfix"
    with raises(sigver.XmlsecError):
        sigver.parse_xmlsec_output(output4)


def test_cert_trailing_newlines_ignored():
    assert read_cert_from_file(full_path("extra_lines.crt")) \
           == read_cert_from_file(full_path("test_2.crt"))


def test_invalid_cert_raises_error():
    with raises(CertificateError):
        read_cert_from_file(full_path("malformed.crt"))


def test_der_certificate_loading():
    assert read_cert_from_file(full_path("test_1.der"), "der") == \
           read_cert_from_file(full_path("test_1.crt"))


if __name__ == "__main__":
    # t = TestSecurity()
    # t.setup_class()
    # t.test_sign_assertion()

    test_sha256_signing()
