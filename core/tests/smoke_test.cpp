#include "dedup.h"
#include <cstring>
int main() { return std::strcmp(dedup::version(), "0.1.0") == 0 ? 0 : 1; }
