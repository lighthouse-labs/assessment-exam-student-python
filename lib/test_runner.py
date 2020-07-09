import pytest
from pytest_jsonreport.plugin import JSONReport

from lib.api import API, SubmissionError

import datetime as dt
import json
import hashlib
from math import floor
import os 
import sys

class HiddenPrints:

    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout


class TestRunner:

    def __init__(self, question_number):
        self.start_time = dt.datetime.now()
        self.question_number = question_number

    
    def pad_number(self, number):
        if int(number) < 10:
            return f'0{number}'
        else:
            return str(number)

    
    def get_test_file_path(self):
        return f"tests/test_{self.pad_number(self.question_number)}.py"

    
    def load_exam_data(self):
        with open('./.exam-data', 'r') as f:
            self.exam_data = json.loads(f.read())


    def get_student_code(self):
        with open(f"answers/question_{self.pad_number(self.question_number)}.py", 'r') as f:
            return f.read() 
    

    def get_test_file_hash(self):
        with open(self.get_test_file_path(), 'r') as f:
            test_file_content = f.read()
        
        return hashlib.md5(test_file_content.encode()).hexdigest()

    
    def get_test_errors(self):
        if self.json_report['exitcode'] == 0:
            return []
        else:
            return [test_result for test_result in self.json_report['tests'] 
                    if test_result['outcome'] == 'failed']


    def get_request_body(self):
        dct = {
            'examId': self.exam_data['exam_id'],
            'questionNumber': self.question_number,
            'lintResults': None,
            'testResults': self.get_test_results(),
            'testFileHash': self.get_test_file_hash(),
            'studentCode': self.get_student_code(),
            'errors' : self.get_test_errors()
        }

        return dct

    
    def get_test_results(self):
        dct = {
            'suites': 1,
            'tests': self.json_report['summary']['total'],
            'passes': self.json_report['summary']['total'] - self.json_report['summary']['failed'],
            'pending': self.json_report['summary']['total'] - self.json_report['summary']['collected'],
            'failures': self.json_report['summary']['failed'],
            'start': str(self.start_time),
            'end': str(self.end_time),
            'duration' : self.json_report['duration']
        }

        return dct


    def print_results(self,results):
        print('Overall Score')
        print('------------')

        questions = results['scores']
        for q in questions:
            print(f'Q{q["questionNumber"]}. {int(q["score"])/ int(q["maxScore"])}')


        time_remaining = float(results['remainingTime'])
        if time_remaining > 0:
            hours = floor(time_remaining / 60)
            minutes = floor(time_remaining % 60)

            print(f"Time Remaining: {hours}h{minutes}m")

        else:
            print('Time Remaining: None (Submission still accepted)')


    def run(self):
        self.load_exam_data()

        plugin = JSONReport()
        with HiddenPrints():
            pytest.main([self.get_test_file_path()], plugins=[plugin])

        self.json_report = plugin.report
        self.end_time = dt.datetime.now()

        try:
            self.request_body = self.get_request_body()
            res =  API().submit_results(request_body = self.request_body,
                                        exam_id = self.exam_data['exam_id'], 
                                        exam_token = self.exam_data['token'])
        
            self.print_results(results=res)
        
        except SubmissionError as e:
            print(e)

