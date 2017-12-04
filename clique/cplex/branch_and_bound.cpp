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

    int num_vertices = 0;
    static vertex_matrix adjacency_matrix = {};
    static double time_limit = 0;
    static auto start_time = _chrono::now();


    /* heuristic-related */
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

    inline std::map<vertex, int> get_color_sets(const vertex_array& vertices)
    {
        auto size = vertices.size();
        assert(size == num_vertices);
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
        return colors;
    }
    /* heuristic-related */


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

    template<typename T>
    bool is_almost_equal(T a, T b, int units_in_last_place = 2)
    {
        return std::abs(a - b) <= std::numeric_limits<T>::epsilon()
                                  * std::max(std::abs(a), std::abs(b))
                                  * units_in_last_place
               || std::abs(a - b) < std::numeric_limits<T>::min(); // subnormal result
    }

    #define ERROR_OUT(msg) std::cerr << "---\n" << msg << "\n---" << std::endl;

    std::string pretty_print(const IloIntArray& vertices)
    {
        std::string s;
        assert(vertices.getSize() == num_vertices);
        for (int i = 0; i < num_vertices; i++)
        {
            if (vertices[i] == 1)
            {
                s.append(std::to_string(i + 1));
                s.append(" ");
            }
        }
        return s;
    }

    std::string pretty_print(const IloNumArray& vertices)
    {
        std::string s;
        assert(vertices.getSize() == num_vertices);
        for (int i = 0; i < num_vertices; i++)
        {
            if (is_almost_equal(vertices[i], 1.0))
            {
                s.append(std::to_string(i + 1));
                s.append(" ");
            }
        }
        return s;
    }

    static inline IloEnv& get_cplex_env()
    {
        static IloEnv cplex_env;
        return cplex_env;
    }

    static inline IloNumVarArray& get_X()
    {
        assert(num_vertices != 0);
        static IloNumVarArray vars(get_cplex_env(), num_vertices, 0.0, 1.0);
        return vars;
    }

    static inline IloModel& get_cplex_model()
    {
        static IloModel cplex_model(get_cplex_env());
        return cplex_model;
    }

    static inline IloCplex& get_cplex_algo()
    {
        static IloCplex cplex_algo(get_cplex_model());
        cplex_algo.setParam(IloCplex::Param::RootAlgorithm, IloCplex::Concurrent);
        return cplex_algo;
    }

    static inline IloObjective& get_cplex_objective()
    {
        static IloObjective obj_function = IloMaximize(get_cplex_env());
        return obj_function;
    }

#define SOLVE_WITH_HEURISTIC 1

    void set_up_cplex(const vertex_matrix& adj_m, const std::map<vertex, int>& color_sets = {}, int colors_num = 0)
    {
        auto& obj_function = get_cplex_objective();
        auto& vars = get_X();
        for (int i = 0; i < num_vertices; ++i)
        {
            obj_function.setLinearCoef(vars[i], 1);
        }

        auto& env = get_cplex_env();
        IloConstraintArray constraints(env);

#if SOLVE_WITH_HEURISTIC
        std::vector<vertex_array> independent_sets(colors_num, vertex_array{});
        for (const auto& vertex_color_pair : color_sets)
        {
            // colors start from 1, not 0:
            independent_sets[vertex_color_pair.second-1].emplace_back(vertex_color_pair.first);
        }
        for (const auto& set : independent_sets)
        {
            IloExpr expr(env);
            for (const auto& vertex : set)
            {
                expr += vars[vertex];
            }
            constraints.add(IloConstraint(expr <= 1.0));
        }
#else

        for (int row_num = 0, size = adj_m.size(); row_num < size; ++row_num)
        {
            for (int i = 0; i < num_vertices; ++i)
            {
                if (row_num != i && adj_m[row_num][i] == 0)
                {
                    IloExpr expr(env);
                    expr += vars[row_num] + vars[i];
                    constraints.add(IloConstraint(expr <= 1.0));
                }
            }
        }
#endif
        auto& model = get_cplex_model();
        model.add(get_cplex_objective());
        model.add(constraints);
    }

    std::tuple<std::vector<IloNum>, int> get_noninteger_values(const IloNumArray& values)
    {
        std::vector<IloNum> out{};
        int index_of_max_noninteger = 0;
        out.reserve(num_vertices);
        for (int i = 0; i < num_vertices; i++)
        {
            const IloNum& value = values[i];
            if (!is_almost_equal(value, 0.0) && !is_almost_equal(value, 1.0))
            {
                out.emplace_back(value);
                if (value > values[index_of_max_noninteger])
                {
                    index_of_max_noninteger = i;
                }
            }
        }
        return std::make_tuple(out, index_of_max_noninteger);
    }

    static int global_ub = 0;

    enum class bnb_status : int
    {
        found_optimal_solution = 0,
        found_integer_solution = 1,
        nothing_found = 2,
        error = 3
    };

    // optimal solution will be stored in these variables:
    int max_clique_size = 0;
    IloIntArray max_clique_values(get_cplex_env());

    /**
     * @brief BnB main function to execute branching logic to find integer solution
     *
     * @param[out] objective_value  Function value. Also represents current best value found.
     * @param[out] optimal_values   Values array. Also represents current best solution.
     * @return bnb_status
     */
    bnb_status branch_and_bound() try
    {
        auto& cplex = get_cplex_algo();
        if (!cplex.solve())
        {
            ERROR_OUT("IloCplex::solve() failed");
            std::exit(EXIT_FAILURE);
        }

        auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(_chrono::now() - start_time);
        if (elapsed.count() > time_limit)
        {
            throw std::runtime_error("Out of time");
        }

        // if non-integer solution is worse than current best - return immediately
        auto current_obj_val = static_cast<int>(cplex.getObjValue());
        if (max_clique_size >= current_obj_val)
            return bnb_status::nothing_found;

        auto& env = get_cplex_env();
        IloNumArray vals(env);
        cplex.getValues(vals, get_X());
        auto result = get_noninteger_values(vals);
        auto nonInts = std::get<0>(result);
        if (!nonInts.empty())
        {
            auto index_to_branch = std::get<1>(result);
            IloExpr expr(env);
            auto& array_of_X = get_X();
            expr += array_of_X[index_to_branch];
            IloConstraint c1(expr >= 1.0);
            auto& model = get_cplex_model();
            model.add(c1);
            auto sts1 = branch_and_bound();
            if (sts1 == bnb_status::found_optimal_solution)
                return sts1;
            model.remove(c1);

            IloConstraint c2(expr <= 0.0);
            model.add(c2);
            auto sts2 = branch_and_bound();
            if (sts2 == bnb_status::found_optimal_solution)
                    return sts2;
            model.remove(c2);
        }
        else
        {
            max_clique_size = current_obj_val;
            max_clique_values = vals.toIntArray();
            if (max_clique_size == global_ub)
                return bnb_status::found_optimal_solution; // helps to reduce unnecessary calculations
            return bnb_status::found_integer_solution;
        }
    }
    catch (const IloException& e)
    {
        std::string msg(e.getMessage());
        ERROR_OUT(msg);
        std::exit(EXIT_FAILURE);
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

    vertex_array all_vertices{};
    for (int i = 0; i < num_vertices; i++)
    {
        all_vertices.emplace_back(i);
    }

    start_time = _chrono::now();

#if SOLVE_WITH_HEURISTIC
    auto color_sets = get_color_sets(all_vertices);
    auto colors_num = std::max_element(color_sets.begin(), color_sets.end(),
                                       [](const auto& p1, const auto& p2)
    {
        return p1.second < p2.second;
    })->second;
    set_up_cplex(adjacency_matrix, color_sets, colors_num);
#else
    set_up_cplex(adjacency_matrix);
#endif
    auto& cplex = get_cplex_algo();
    cplex.setOut(get_cplex_env().getNullStream());
    if (!cplex.solve())
    {
        ERROR_OUT("IloCplex::solve() failed");
        return 1;
    }
    global_ub = static_cast<int>(cplex.getObjValue());
#if SOLVE_WITH_HEURISTIC
    if (global_ub > colors_num) global_ub = colors_num; // better upper-bound
#endif

    branch_and_bound();
    auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(_chrono::now() - start_time);
    std::cout << elapsed.count() << " " << static_cast<int>(max_clique_size) << " " << pretty_print(max_clique_values) << std::endl;
    return 0;
}
catch (const std::exception&)
{
    get_cplex_algo().end();
    std::cout << time_limit << " " << static_cast<int>(max_clique_size) << " " << pretty_print(max_clique_values) << std::endl;
    return 1;
}
