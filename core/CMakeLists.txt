cmake_minimum_required(VERSION 3.16)
project(libdedup LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(dedup STATIC src/version.cpp)
target_include_directories(dedup PUBLIC include)

enable_testing()
add_executable(smoke_test tests/smoke_test.cpp)
target_link_libraries(smoke_test PRIVATE dedup)
add_test(NAME smoke COMMAND smoke_test)
# Next: sha256 (OpenSSL/libsodium), zstd, sqlite3, libcurl, nlohmann_json via vcpkg or FetchContent.
