"""Fetch and validate the public timetable before replacing the published JSON."""
import datetime as dt
import json
import os
import subprocess
from pathlib import Path

from timetable import SOURCE, parse_schedule

DEST = Path(__file__).resolve().parents[1] / 'site' / 'schedule.json'


def main():
    response = subprocess.run(['curl', '--fail', '--silent', '--show-error',
        '--location', '--connect-timeout', '8', '--max-time', '20',
        '--retry', '2', '--retry-delay', '3', '--max-filesize', '5000000',
        '--user-agent', 'PersonalTimetable/1.0', SOURCE], capture_output=True, timeout=90)
    if response.returncode:
        raise RuntimeError('Could not download timetable: ' + response.stderr.decode('utf-8', errors='replace'))
    data = parse_schedule(response.stdout.decode('utf-8'))
    data.update(checkedAt=dt.datetime.now(dt.timezone.utc).isoformat(),
                checkedEpoch=dt.datetime.now(dt.timezone.utc).timestamp())
    temp = DEST.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, DEST)
    print('Validated and updated both weeks:', sum(len(day) for week in data['weeks'].values() for day in week), 'lessons')


if __name__ == '__main__':
    main()
