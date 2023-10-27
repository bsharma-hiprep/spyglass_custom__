import random

import datajoint as dj
from spyglass.common.common_behav import RawPosition  # noqa: F401
from spyglass.common.common_nwbfile import Nwbfile  # noqa: F401
from spyglass.common.common_subject import Subject  # noqa: F401
from spyglass.spike_sorting.spike_sorting import CuratedSpikeSorting  # noqa: F401

from ..utils.schema_prefix import schema_prefix

schema = dj.schema(schema_prefix + "_example")  # CHANGE THIS


@schema
class SubjBlinded(dj.Manual):
    definition = """ # comment 
    subject_id: uuid # id 
    ---
    -> Subject.proj(actual_id='subject_id')
    """

    @property  # Static information, Table.property
    def pk(self):
        return "subject_id"

    @staticmethod  # Basic func with no referece to self instance
    def _subj_dict(id):
        """Return the subject dict"""
        return {"subject_id": id}

    @classmethod  # Class, not instance. Table.func(), not Table().func()
    def example(cls):
        pass  # Not doing anything

    def blind_subjs(self, restriction):
        """Import all subjects selected by the restriction"""
        subj_keys = (Subject & restriction).fetch("KEY")
        insert_keys = []
        for key in subj_keys:
            insert_keys.append(
                {
                    **self._subj_dict(dj.hash.key_hash(key)),
                    "actual_id": key["subject_id"],
                }
            )
        self.insert(insert_keys, skip_duplicates=True)

    def return_subj(self, key):
        """Return the entry in subject table"""
        if isinstance(key, dict):  # get rid of extra values
            key = key["subject_id"]
        key = self._subj_dict(key)
        actual_id = (self & key).fetch1("actual_id")
        return Subject & {"subject_id": actual_id}


@schema
class MyTable(dj.Manual):
    definition = """
    blinded_nwb_file_name : uuid
    ---
    -> Nwbfile.proj(actual_nwb_file_name='nwb_file_name')
    """

    def blind_file(self, restriction):
        pass

    def return_file(self, key):
        pass


@schema
class MyParams(dj.Lookup):
    definition = """
    param_name: varchar(32)
    ---
    params: blob
    """
    contents = [
        ["example1", {"A": 1, "B": 2}],
        ["example2", {"A": 3, "B": 4}],
    ]

    @classmethod
    def insert_default(cls):
        cls.insert(cls.contents, skip_duplicates=True)


@schema
class MyAnalysisSelection(dj.Manual):
    definition = """
    -> SubjBlinded
    -> MyParams
    """

    def insert_all(self, param_name="example1"):
        """Insert all subjects with given param name"""
        self.insert(
            [
                {**subj_key, "param_name": param_name}
                for subj_key in SubjBlinded.fetch("KEY")
            ],
            skip_duplicates=True,
        )


@schema
class MyAnalysis(dj.Computed):
    definition = """
    -> MyAnalysisSelection
    """

    class DataAcquisitionDevice(dj.Part):
        definition = """
        -> MyAnalysis
        ---
        result: int
        """

    def make(self, key):
        # Run analysis and save the result
        result = 0

        this_subj = SubjBlinded().return_subj(key["subject_id"])
        this_nwb = NwbBlinded().return_file(key["nwb_file_name"])

        these_param = (MyParams & {"param_name": key["param_name"]}).fetch1(
            "params"
        )

        this_sort = CuratedSpikeSorting() * this_nwb

        for pos_obj in RawPosition().PosObject * this_subj:
            result += len((RawPosition.PosObject & pos_obj).fetch1_dataframe())

        for value in these_param.values():
            result += value

        for i in range(10):
            result += self._get_random_result()
            self.DataAcquisitionDevice.insert1(dict(key, result=result))

        self.insert1(key)

    def _get_random_result(self):
        return random.randint(0, 100)
