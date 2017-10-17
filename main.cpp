#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <cstdint>
#include <vector>
#include <chrono>

namespace
{
    using vertex = std::uint64_t;
    using vertex_array = std::vector<std::uint64_t>;
    using vertex_matrix = std::vector<vertex_array>;

    std::vector<std::string> split(std::string& s, const std::string& delim)
    {
        std::vector<std::string> out = {};
        std::stringstream ss(s);
        std::size_t pos = 0;
        std::string token;
        while ((pos = s.find(delim)) != std::string::npos) {
            token = s.substr(0, pos);
            out.push_back(token);
            s.erase(0, pos + delim.size());
        }
        out.push_back(s);
        return out;
    }

    struct clique
    {
        vertex_array m_vertices = {};
        std::size_t m_heuristic_size = 0;
        std::size_t size()
        {
            auto s = m_vertices.size();
            return s * (s - 1) / 2;
        }
    };


    static vertex_matrix adjacency_matrix = {};
    static clique optimal_clique = {};

    vertex_array get_candidates(vertex v)
    {
        vertex n_vertices = static_cast<vertex>(adjacency_matrix.size());
        const auto& row = adjacency_matrix[v];
        vertex_array C = {};
        for (vertex i = v + 1; i < n_vertices; ++i)
        {
            if (row[i] > 0 /*&& i > v*/ && v != i) { C.push_back(i); }
        }
        return C;
    }

    void max_clique(const clique& curr_Q, const vertex_array& C)
    {
    }
}

int main(int argc, char* argv[])
{
    using _chrono = std::chrono::steady_clock;
    if (argc < 2) return 1;
    std::uint64_t time_limit = std::atoll(argv[2]);
    std::ifstream f(argv[1]);
    if (!f.good()) return 1;
    std::string line;
    vertex n_vertices = 0;
    std::size_t n_edges = 0;
    const char default_delim[] = " ";
    auto start = _chrono::now();
    while (!f.eof())
    {
        std::getline(f, line);
        auto l0 = line.substr(0, 1);
        if (l0.compare("c") == 0) continue;
        auto parsed = split(line, default_delim);
        if (l0.compare("p") == 0) // format: p col <n_vertices> <n_edges>
        {
            n_vertices = std::atoll(parsed[2].c_str());
            n_edges = std::atoll(parsed[3].c_str());
            adjacency_matrix.resize(n_vertices, vertex_array(n_vertices, 0));
        }
        if (l0.compare("e") == 0) // format: e <vertex1> <vertex2>
        {
            auto v1 = static_cast<vertex>(std::atoll(parsed[1].c_str())) - 1,
                 v2 = static_cast<vertex>(std::atoll(parsed[2].c_str())) - 1;
            adjacency_matrix[v1][v2]++;
            adjacency_matrix[v2][v1]++;
        }
    }
    auto end = _chrono::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(end - start);
    std::cout << "Parsing took " << elapsed.count() << " seconds" << std::endl;

    return 0;
}
