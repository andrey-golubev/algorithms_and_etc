#define ILOUSESTL
using namespace std;
#include "ilocplex.h"

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
    using vertex = std::uint32_t;
    using vertex_array = std::vector<vertex>;
    using vertex_matrix = std::vector<vertex_array>;
    using _chrono = std::chrono::steady_clock;

    struct clique
    {
        vertex_array m_vertices = {};
        vertex_array m_candidates = {};
    };


    std::size_t num_vertices = 0;
    static vertex_matrix adjacency_matrix = {};
    static clique optimal_clique = {};

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

    inline vertex_array get_connected(vertex v, vertex start_index = 0)
    {
        vertex n_vertices = static_cast<vertex>(adjacency_matrix.size());
        const auto& row = adjacency_matrix[v];
        vertex_array C = {};
        // TODO: verify if can calculate from v + 1:
        for (vertex i = start_index; i < n_vertices; ++i)
        {
            if (row[i] > 0) { C.push_back(i); }
        }
        return C;
    }

    vertex_array find_candidates(const clique& clq, vertex vertex_to_be_added)
    {
        vertex_array out = {};
        auto connected = get_connected(vertex_to_be_added);
        for (const auto& known_candidate : clq.m_candidates)
        {
            for (const auto& possible_candidate : connected)
            {
                if (possible_candidate == known_candidate)
                    out.push_back(possible_candidate);
            }
        }

        return out;
    }

    inline std::uint32_t colors(const vertex_array& vertices)
    {
        auto size = vertices.size();
        if (size <= 0) return 0;
        std::map<vertex, int> colors;

        for (const auto& vertex : vertices)
        {
            std::vector<int> neighbour_colors;
            for (const auto& neighbour : get_connected(vertex))
            {
                neighbour_colors.push_back(colors[neighbour]);
            }

            bool vertex_colored = false;
            int supposed_color = 1;
            while (vertex_colored != true)
            {
                bool color_of_neighbour = false;
                for (const auto& color : neighbour_colors)
                    if (color == supposed_color)
                    {
                        color_of_neighbour = true;
                        break;
                    }
                if (color_of_neighbour)
                {
                    supposed_color++;
                    continue;
                }
                colors[vertex] = supposed_color;
                vertex_colored = true;
            }
        }
        return std::max_element(colors.begin(), colors.end())->second;
    }

    inline std::uint32_t upper_bound(const clique& Q)
    {
        return Q.m_vertices.size() + colors(Q.m_candidates);
    }

    void max_clique(const clique& Q)
    {
        auto ub = upper_bound(Q);
        if (ub <= optimal_clique.m_vertices.size()) return;
        if (Q.m_candidates.size() == 0)
        {
            optimal_clique = Q;
            return;
        }

        auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(_chrono::now() - start_time);
        if (elapsed.count() > time_limit)
        {
            throw std::runtime_error("Out of time");
        }

        for (const auto& candidate : Q.m_candidates)
        {
            auto temp_q = Q;
            temp_q.m_candidates = find_candidates(temp_q, candidate);
            temp_q.m_vertices.push_back(candidate);
            max_clique(temp_q);
        }
    }

    vertex_matrix get_constraints(const vertex_matrix& adj_m)
    {
        vertex_matrix all_constraints{};
        for (int row_num = 0, size = adj_m.size(); row_num < size; ++row_num)
        {
            for (int i = 0; i < num_vertices; ++i)
            {
                if (row_num != i && adj_m[row_num][i] == 0)
                {
                    vertex_array constraint_row_coeffs(num_vertices, 0);
                    constraint_row_coeffs[row_num] = 1;
                    constraint_row_coeffs[i] = 1;
                    all_constraints.push_back(std::move(constraint_row_coeffs));
                }
            }
        }
        return all_constraints;
    }

    std::string pretty_print(const clique& Q)
    {
        std::string s;
        for (const auto& vertex : Q.m_vertices)
        {
            s.append(std::to_string(vertex + 1));
            s.append(" ");
        }
        return s;
    }

#define ERROR_OUT(msg) std::cerr << msg << std::endl;


// CPLEX specific:
    static IloEnv& get_cplex_env()
    {
        static IloEnv cplex_env;
        return cplex_env;
    }

    static IloNumVarArray& get_X()
    {
        assert(num_vertices != 0);
        static IloNumVarArray vars(get_cplex_env(), num_vertices);
        return vars;
    }

    static IloModel& get_cplex_model()
    {
        static IloModel cplex_model(get_cplex_env());
//        cplex_model.add(IloMaximize(get_cplex_empty_vars()));
        return cplex_model;
    }

    static IloCplex& get_cplex_algo()
    {
        static IloCplex cplex_algo(get_cplex_model());
        cplex_algo.setParam(IloCplex::Param::RootAlgorithm, IloCplex::Concurrent);
        return cplex_algo;
    }

    static std::vector<IloNumVarArray> get_cplex_constraints(const vertex_matrix& adj_m)
    {
        auto& env = get_cplex_env();
        std::vector<IloNumVarArray> all_constaints{};
        for (int row_num = 0, size = adj_m.size(); row_num < size; ++row_num)
        {
            for (int i = 0; i < num_vertices; ++i)
            {
                if (row_num != i && adj_m[row_num][i] == 0)
                {
                    IloNumVarArray vars(env, num_vertices);
//                    vars[row_num] = IloNumVar(1);
//                    vars[i] = 1;
                    all_constaints.emplace_back(vars);
                }
            }
        }
        return all_constaints;
    }

    static IloObjective& get_cplex_objective()
    {
        static IloObjective obj_function = IloMaximize(get_cplex_env());
        auto& vars = get_X();
        for (int i = 0; i < num_vertices; ++i)
        {
            obj_function.setLinearCoef(vars[i], 1);
        }
    }

    void set_up_cplex(const vertex_matrix& adj_m)
    {
        IloRangeArray column(get_cplex_env());
        get_cplex_model().add(get_cplex_objective());
    }
}

int main(int argc, char* argv[]) try
{
    if (argc < 3)
    {
        ERROR_OUT("Command-line arguments: <file> <time limit>. Ex: ./mlp graph.clq 1000");
        return 1;
    }
    std::ifstream f(argv[1]);
    if (!f.good())
    {
        ERROR_OUT("File is unreachable/not found");
        return 1;
    }
    time_limit = std::atof(argv[2]); // in seconds
    if (time_limit == 0)
    {
        ERROR_OUT("Time limit is incorrect");
        return 1;
    }

    std::string line;
//    std::size_t n_edges = 0;
    static constexpr char default_delim[] = " ";
    while (!f.eof())
    {
        std::getline(f, line);
        auto l0 = line.substr(0, 1);
        if (l0.compare("c") == 0) continue;
        auto parsed = split(line, default_delim);
        if (l0.compare("p") == 0) // format: p col <n_vertices> <n_edges>
        {
            num_vertices = std::atoll(parsed[2].c_str());
//            n_edges = std::atoll(parsed[3].c_str());
            adjacency_matrix.resize(num_vertices, vertex_array(num_vertices, 0));
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

    auto constraints = get_constraints(adjacency_matrix);
    auto v = get_X();

//    get_cplex_algo().extract(get_cplex_model());

    auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(_chrono::now() - start_time);
    std::cout << elapsed.count() << " " << optimal_clique.m_vertices.size() << " " << pretty_print(optimal_clique) << std::endl;

    return 0;
}
catch (const std::exception&)
{
    std::cout << time_limit << " " << optimal_clique.m_vertices.size() << " " << pretty_print(optimal_clique) << std::endl;
    return 1;
}
