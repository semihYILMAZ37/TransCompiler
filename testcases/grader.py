import os
import subprocess
import csv
import logging
import shutil


def setup_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def execute_commands(student_dir, input_file, error_case=False):
    commands = [
        f"./advcalc2ir {input_file}",
        f"lli {input_file.replace('.adv', '.ll')}",
    ]
    process = subprocess.Popen("make", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=student_dir)
    stdout, stderr = process.communicate()
    if not os.path.exists(f"{student_dir}/advcalc2ir"):
        logger.error(f"Error: advcalc2ir not found for {student_dir}")
        return stdout, stderr, False
        
    for command in commands:
        try: 
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=student_dir)
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logging.info("Timeout expired before the process finished. Terminating...")
            process.kill()
        stdout, stderr = process.communicate()
        if process.returncode != 0: 
            return stdout, stderr, False
        elif error_case: 
            return stdout, stderr, True
    return stdout, stderr, True

def compare_outputs(student_output, correct_output):
    student_lines = [line for line in student_output.split('\n') if line != ''] 
    correct_lines = [line for line in correct_output.split('\n') if line != '']

    true_positive = 0
    false_positive = 0
    false_negative = 0

    for line in student_lines:
        if line in correct_lines:
            true_positive += 1
            correct_lines.remove(line)
        else:
            false_positive += 1

    false_negative = len(correct_lines)

    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive > 0 else 0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0

    return precision, recall, f1_score

def grade_projects():
    students_dirs = [d.path for d in os.scandir('submissions/') if d.is_dir()]
    input_files = [f.path for f in os.scandir('inputs/') if f.is_file()]
    output_files = [f.replace('inputs', 'outputs').replace('.adv', '_ans.txt') for f in input_files]

    with open('grades.csv', 'w', newline='') as csvfile:
        output_file_names = [os.path.basename(name).replace('.adv', '') for name in input_files]
        fieldnames = ['student'] + [f'ex_{i+1}_{metric}' for i in range(16) for metric in ['Precision', 'Recall', 'F1_Score']]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for student_dir in students_dirs:
            student_name = os.path.basename(student_dir)
            grades = {'student': student_name}
            logger.info(f'Grading projects for student: {student_name}')
            for i, input_file in enumerate(input_files):
                shutil.copy(input_file, student_dir)
                input_file_name = os.path.basename(input_file)
                output_file = os.path.basename(input_file_name).replace('.adv', '')
                error_case = int(input_file_name.replace('.adv', '').split('_')[1]) > 10
                stdout, stderr, success = execute_commands(student_dir, input_file_name, error_case)
                if not success:
                    with open(f'{student_dir}/log.txt', 'w', encoding='utf8') as log_file:
                        try:
                            log_file.write(stderr.decode('utf-8'))
                        except UnicodeDecodeError:
                            log_file.write(stderr.decode('ISO-8859-1'))
                    continue
                with open(output_files[i], 'r') as correct_output_file:
                    correct_output = correct_output_file.read()
                precision, recall, f1_score = compare_outputs(stdout.decode(), correct_output)
                grades[f'{output_file}_Precision'] = f'{precision}' 
                grades[f'{output_file}_Recall'] = f'{recall}'
                grades[f'{output_file}_F1_Score'] = f'{f1_score}'
                with open(f'{student_dir}/{input_file_name.replace(".adv", ".out")}', 'w') as output_file:
                    output_file.write(stdout.decode())
            writer.writerow(grades)

if __name__ == "__main__":
    logger = setup_logger()
    grade_projects()
