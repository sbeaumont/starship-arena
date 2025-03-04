from fastapi.testclient import TestClient

from arena.api.fastapimain import app


client = TestClient(app)

def test_add_commands():
    commands = {
        'lines': [
            '1: A25',
            '2: Fire R1 90',
            '3:A25'
        ]
    }
    response = client.post('/game/apitest/ship/Blaster/commands', json=commands)
    print(response.json())
    assert response.status_code == 200

def test_add_wrong_commands():
    commands = {
        'lines': [
            '1: A40',
            '2: Frrrr R1 90',
            '3:A25',
            '3:A5',
            'flrarlakf'
        ]
    }
    response = client.post('/game/apitest/ship/Blaster/commands', json=commands)
    print(response.json())
    assert response.status_code == 400

if __name__ == '__main__':
    test_add_commands()
    test_add_wrong_commands()