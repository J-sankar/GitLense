import pytest
from app.services.code_parser import extract_chunks

@pytest.fixture
def sample_python_code():
    return """
    # Copyright 2019 The Kubernetes Authors.
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

from kubernetes import config
from kubernetes.client import Configuration
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream


def exec_commands(api_instance):
    name = 'busybox-test'
    resp = None
    try:
        resp = api_instance.read_namespaced_pod(name=name,
                                                namespace='default')
    except ApiException as e:
        if e.status != 404:
            print(f"Unknown error: {e}")
            exit(1)

    if not resp:
        print(f"Pod {name} does not exist. Creating it...")
        pod_manifest = {
            'apiVersion': 'v1',
            'kind': 'Pod',
            'metadata': {
                'name': name
            },
            'spec': {
                'containers': [{
                    'image': 'busybox',
                    'name': 'sleep',
                    "args": [
                        "/bin/sh",
                        "-c",
                        "while true;do date;sleep 5; done"
                    ]
                }]
            }
        }
        resp = api_instance.create_namespaced_pod(body=pod_manifest,
                                                  namespace='default')
        while True:
            resp = api_instance.read_namespaced_pod(name=name,
                                                    namespace='default')
            if resp.status.phase != 'Pending':
                break
            time.sleep(1)
        print("Done.")

    # Calling exec and waiting for response
    exec_command = [
        '/bin/sh',
        '-c',
        'echo This message goes to stderr; echo This message goes to stdout']
    # When calling a pod with multiple containers running the target container
    # has to be specified with a keyword argument container=<name>.
    resp = stream(api_instance.connect_get_namespaced_pod_exec,
                  name,
                  'default',
                  command=exec_command,
                  stderr=True, stdin=False,
                  stdout=True, tty=False)
    print("Response: " + resp)

    # Calling exec interactively
    exec_command = ['/bin/sh']
    resp = stream(api_instance.connect_get_namespaced_pod_exec,
                  name,
                  'default',
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=False,
                  _preload_content=False)
    commands = [
        "echo This message goes to stdout",
        "echo \"This message goes to stderr\" >&2",
    ]

    while resp.is_open():
        resp.update(timeout=1)
        if resp.peek_stdout():
            print(f"STDOUT: {resp.read_stdout()}")
        if resp.peek_stderr():
            print(f"STDERR: {resp.read_stderr()}")
        if commands:
            c = commands.pop(0)
            print(f"Running command... {c}\n")
            resp.write_stdin(c + "\n")
        else:
            break

    resp.write_stdin("date\n")
    sdate = resp.readline_stdout(timeout=3)
    print(f"Server date command returns: {sdate}")
    resp.write_stdin("whoami\n")
    user = resp.readline_stdout(timeout=3)
    print(f"Server user is: {user}")
    resp.close()


def main():
    config.load_kube_config()
    try:
        c = Configuration().get_default_copy()
    except AttributeError:
        c = Configuration()
        c.assert_hostname = False
    Configuration.set_default(c)
    core_v1 = core_v1_api.CoreV1Api()

    exec_commands(core_v1)


if __name__ == '__main__':
    main()

"""

@pytest.fixture
def sample_java_code():
    return """
    package org.tunes.controllers;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import org.tunes.components.TokenStore;
import org.tunes.dto.SongInfo;
import org.tunes.services.SongMapper;
import org.tunes.services.SpotifySearch;
import reactor.core.publisher.Mono;
import org.tunes.dto.songMetaDTO;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeoutException;

@RestController
@RequestMapping("/songmeta")
@Slf4j
public class Song_meta {

    private final ObjectMapper prettyMapper = new ObjectMapper()
            .enable(SerializationFeature.INDENT_OUTPUT);

    private final WebClient webClient;
    private final SpotifySearch spotifySearch;
    private final SongMapper mapper;
    private final TokenStore tokenStore;

    // ----- constructor injection -----
    public Song_meta(WebClient.Builder webClientBuilder,
                     SpotifySearch spotifySearch,
                     SongMapper mapper,
                     TokenStore tokenStore) {
        this.webClient = webClientBuilder.baseUrl("http://localhost:8000").build();
        this.spotifySearch = spotifySearch;
        this.mapper = mapper;
        this.tokenStore = tokenStore;
    }

    // ----- POST endpoint to send song info to n8n -----
    @PostMapping("/send")
    public Mono<String> sendSongMeta(@RequestParam String query) {
        // 1️⃣ Get a valid access token
        String access = tokenStore.getValidAccessToken(5);   // demo uid = 5

        // 2️⃣ Get song info
        Map<String, Object> songResponse = spotifySearch.RequestSong(
                access, query,
                new SpotifySearch.SearchSong(),"1","0");

        SongInfo song = mapper.extractTrack(songResponse);

        // 3️⃣ Build JSON payload for n8n
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("songName", song.getSongName());
        requestBody.put("artistName", song.getArtistName());
        requestBody.put("songYear", song.getReleaseDate());

        // 4️⃣ Send POST to n8n webhook (wait max 60s)
        return webClient.post()
                .uri("/webhook-test/songmeta")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(requestBody)
                .retrieve()
                .bodyToMono(String.class)
                .timeout(Duration.ofSeconds(80))  // ⏱ Wait max 1 minute
                .doOnNext(response -> {
                    try {
                        Object json = prettyMapper.readValue(response, Object.class);
                        String prettyJson = prettyMapper.writeValueAsString(json);
                        System.out.println("\n=== Response from n8n ===\n" + prettyJson + "\n=========================\n");
                        log.info("Response from n8n:\n{}", prettyJson);
                    } catch (Exception e) {
                        System.out.println("Raw n8n response: " + response);
                        log.warn("Could not pretty-print n8n response", e);
                    }
                })
                .onErrorResume(TimeoutException.class, e -> {
                    String msg = "⏳ n8n did not respond within 60 seconds.";
                    log.warn(msg);
                    return Mono.just(msg);
                })
                .onErrorResume(WebClientResponseException.class, e -> {
                    String msg = "❌ n8n returned an error: " + e.getStatusCode() + " " + e.getResponseBodyAsString();
                    log.error(msg);
                    return Mono.just(msg);
                });
    }


    // ----- POST endpoint to receive emotional analysis -----
    @PostMapping("/receive")
    public ResponseEntity<String> receiveEmotion(@RequestBody songMetaDTO dto) {

        try {
            String prettyJson = prettyMapper.writeValueAsString(dto);
            System.out.println("\n=== Received Emotion JSON ===\n" + prettyJson + "\n==============================\n");
            log.info("Received emotion payload:\n{}", prettyJson);
        } catch (Exception e) {
            log.warn("Could not pretty-print payload", e);
            log.info("Raw payload: {}", dto);
        }

        // Additional processing can go here (e.g., save to DB)
        return ResponseEntity.ok("Payload received");
    }
}
"""


def test_supported_python(sample_python_code):
    result = extract_chunks(file_path="python/examples/api_discovery.py",content=sample_python_code,language="py")
    chunks = result["chunks"]
    metadata = result["metadata"]
    assert len(chunks) == 2

    assert metadata["path"] == "python/examples/api_discovery.py"
    assert metadata["language"] == "py"

    assert "import time" in metadata["imports"]
    assert "from kubernetes import config" in metadata["imports"]
    assert len(metadata["imports"]) == 6

    extracted_names = [c["name"] for c in chunks]
    assert "exec_commands" in extracted_names
    assert "main" in extracted_names

    for chunk in chunks:
       
        assert chunk["parent_scope"] == "python/examples/api_discovery.py"
        
        
        assert chunk["language"] == "py"
        assert chunk["type"] == "function_definition"
        
    
    exec_chunk = next(c for c in chunks if c["name"] == "exec_commands")

    assert exec_chunk["start_line"] > 20 
    assert "resp = None" in exec_chunk["code"]

    
    main_chunk = next(c for c in chunks if c["name"] == "main")
    assert "core_v1_api.CoreV1Api()" in main_chunk["code"]




def test_supported_java_code(sample_java_code):
    result = extract_chunks(file_path="src/main/java/org/tunes/controllers/Song_meta.java", content=sample_java_code,
                            language="java")
    chunks = result["chunks"]
    metadata = result["metadata"]

    assert len(chunks) == 3

    class_chunk = next(c for c in chunks if c["name"] == "Song_meta")
    assert class_chunk["type"] == "class_declaration"
    assert class_chunk["parent_scope"] == "src/main/java/org/tunes/controllers/Song_meta.java"

    for chunk in chunks :
        assert chunk["language"] == "java"

        if chunk != class_chunk:
            assert chunk["parent_scope"] == class_chunk["name"]


    assert len(metadata["imports"]) == 18
    assert metadata["exports"]== []
    assert metadata["path"] == "src/main/java/org/tunes/controllers/Song_meta.java"
      

