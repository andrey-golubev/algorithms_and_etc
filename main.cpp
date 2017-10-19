#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <cstdint>
#include <vector>
#include <chrono>
#include <limits>
#include <algorithm>
#include <map>

namespace
{
    using vertex = std::uint64_t;
    using vertex_array = std::vector<std::uint64_t>;
    using vertex_matrix = std::vector<vertex_array>;
    using _chrono = std::chrono::steady_clock;

    struct clique
    {
        vertex_array m_vertices = {};
    };


    static vertex_matrix adjacency_matrix = {};
    static clique optimal_clique = {};

//    static std::size_t m_heuristic_size = 0;

    static double time_limit = 0;

    static auto start_time = _chrono::now();

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

    inline vertex_array get_connected(vertex v)
    {
        vertex n_vertices = static_cast<vertex>(adjacency_matrix.size());
        const auto& row = adjacency_matrix[v];
        vertex_array C = {};
        // TODO: verify if can calculate from v + 1:
        for (vertex i = 0; i < n_vertices; ++i)
        {
            if (row[i] > 0) { C.push_back(i); }
        }
        return C;
    }

    vertex_array find_candidates(const vertex_array& vertices)
    {
        auto size = vertices.size();
        std::map<vertex, int> merged_candidates;
        for (const auto& vertex : vertices)
        {
            auto candidates = get_connected(vertex);
            for (const auto& candidate : candidates)
            {
                merged_candidates[candidate]++;
            }
        }

        vertex_array out = {};
        for (const auto& pair : merged_candidates)
        {
            if (pair.second >= size)
            {
                out.push_back(pair.first);
            }
        }
        return out;
    }

    inline std::uint64_t upper_bound(const clique& Q, const vertex_array& C)
    {
        return std::numeric_limits<std::uint64_t>::max();
    }

    void max_clique(const clique& Q, const vertex_array& C)
    {
        auto ub = upper_bound(Q, C);
        if (ub <= optimal_clique.m_vertices.size()) return;
//        if (ub <= m_heuristic_size) return;
        if (C.size() == 0)
        {
            optimal_clique = Q;
            return;
        }

        auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(_chrono::now() - start_time);
        if (elapsed.count() > time_limit)
        {
            throw std::runtime_error("Out of time");
        }

        for (const auto& candidate : C)
        {
            auto temp_q = Q;
            temp_q.m_vertices.push_back(candidate);
            max_clique(temp_q, find_candidates(temp_q.m_vertices));
        }
    }

    std::string pretty_print(const clique& Q)
    {
        std::string s;
        for (const auto& vertex : Q.m_vertices)
        {
            s.append(std::to_string(vertex));
            s.append(" ");
        }
        return s;
    }
}

int main(int argc, char* argv[]) try
{
    if (argc < 2) return 1;
    time_limit = std::atof(argv[2]); // in seconds
    if (time_limit == 0) return 1;
    std::ifstream f(argv[1]);
    if (!f.good()) return 1;

    std::string line;
    vertex n_vertices = 0;
    std::size_t n_edges = 0;
    static constexpr char default_delim[] = " ";
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

    start_time = _chrono::now();
    for (vertex v = 0; v < n_vertices; ++v)
    {
        clique q;
        q.m_vertices.push_back(v);
        max_clique(q, get_connected(v));
    }
    auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(_chrono::now() - start_time);
    std::cout << elapsed.count() << " " << optimal_clique.m_vertices.size() << " " << pretty_print(optimal_clique) << std::endl;

    return 0;
}
catch (const std::exception&)
{
//    std::cout << time_limit << " " << optimal_clique.m_vertices.size() << " " << pretty_print(optimal_clique) << std::endl;
    std::cout << time_limit << " 0 " << pretty_print(optimal_clique) << std::endl;
    return 1;
}
