import pytest  # noqa: F401


async def test_register(client) :
    response = await client.post("/api/v1/auth/register",json={
        "username": "testuser",
        "email":"tester@example.com",
        "password":"random123"
    })
    assert response.status_code == 201
    data = response.json()
    assert "username" in data
    assert data["email"] == "tester@example.com"
    assert "password" not in data


async def test_duplicate_username(client,test_user) :
    response = await client.post("/api/v1/auth/register",json={
        "username": "testuser",
        "email":"anothertester@example.com",
        "password":"random456"
    })
    assert response.status_code == 409


async def test_duplicate_email(client, test_user):
    response = await client.post("/api/v1/auth/register",json={
        "username": "testuser",
        "email": test_user.email,
        "password":"random456"
    })
    assert response.status_code == 409
    

async def test_login(test_user,client):
    response =await client.post("/api/v1/auth/login",json={
        "email": test_user.email,
        "password": "test1234" ,
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in response.cookies
    


async def test_wrong_password(test_user,client):
    response = await client.post("/api/v1/auth/login",json={
        "email": test_user.email,
        "password": "test12345" ,
    })
    assert response.status_code == 401
   


async def test_anauthorized_logout(test_user, client):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401
   


async def test_logout(test_user,client,auth_headers):
    response = await  client.post("/api/v1/auth/logout",headers=auth_headers)
    assert response.status_code == 200
    assert response.cookies.get("refresh_token") is None
   

async def test_token_refresh_flow(client, test_user):
    # 1. Login to get the initial cookie set by the server
    login_data = {"email": test_user.email, "password": "test1234"}
    login_res = await client.post("/api/v1/auth/login", json=login_data)
    assert login_res.status_code == 200
    
    old_access_token = login_res.json()["access_token"]

    response = await client.post("/api/v1/auth/refresh")
    
    assert response.status_code == 200
    data = response.json()
   
    assert "access_token" in data
    assert data.get("access_token") != old_access_token
    
 
    assert "refresh_token" in client.cookies