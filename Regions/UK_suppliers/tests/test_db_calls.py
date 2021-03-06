import pdb
from ..Regional_Run_Files import db_calls
import pgsanity.ecpg
import pandas as pd
from sqlalchemy import text

def test_isConnected(connection):
    if not connection or connection.closed == 1:
        assert False
    assert True

#---------- Test creation of actual test tables--------
def test_create_regDBschema(create_reg_table):
    orgs_ocds_test = create_reg_table
    # Create assertion that data exists in the table too (below just asserts table exists) tablesample?
    assert orgs_ocds_test.exists()

def test_create_srcDBschema(create_src_table):
    ocds_tenders_test = create_src_table
    assert ocds_tenders_test.exists()

def test_create_uploadDBschema(create_upload_table):
    upload_table_test = create_upload_table
    assert upload_table_test.exists()
# -----------------------------------------------------


def test_createRegistryDataSQLQuery(settings):
    # assert settings.reg_data_source
    # query = db_calls.FetchData.createRegistryDataSQLQuery(settings)
    # print(pgsanity.ecpg.check_syntax("select * from;"))
    # print(pgsanity.ecpg.check_syntax('ldgflerffe;'))
    # # both work??
    #https: // stackoverflow.com / questions / 8271606 / postgresql - syntax - check - without - running - the - query
    pass


def test_fetchregData(settings, test_create_reg_table):
    postgresql_db, orgs_ocds_test = test_create_reg_table

    settings.reg_data_source = orgs_ocds_test
    query = db_calls.FetchData.createRegistryDataSQLQuery(settings)

    result = postgresql_db.session.query(orgs_ocds_test).from_statement(text(query))
    # result = postgresql_db.session.query(orgs_ocds_test).from_statement(text("SELECT id, scheme, uri, legalname, source, created_at, orgs_ocds_scheme_id_idx from orgs_ocds_test"))
    # pdb.set_trace()
    # result = postgresql_db.session.query(orgs_ocds_test).all()
    for row in result:
        print(row)


def test_removeTableDuplicates():
    pass


def test_addDataToTable():
    pass


# def test_raw_data_access():
#     # Test that either a raw data file exists or the connection can be made to the database
#     pass
#
# test imported data matches usecols format
## test upload data to db actually uploads it


# Use mocks to avoid having to make live-calls to a function that has an external function call inside it:
# https://realpython.com/python-cli-testing/#pytest
# def initial_transform(data):
#     outside_module.do_something()
#     return data

# Want to test that the data being downloaded is actually the required format? If so, are mocks necessary. Probably, because we won't always want to keep re-testing the db-communication tests
# i.e. don't want to have to re-download test data just to test i.e. a processing function
