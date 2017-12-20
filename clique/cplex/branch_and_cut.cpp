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
        const auto& row = adjacency_matrix[v];
        vertex_array C = {};
        for (vertex i = start_index; i < num_vertices; ++i)
        {
            if (row[i] > 0) { C.push_back(i); }
        }
        return C;
    }
    inline vertex_array get_connected(vertex v, const vertex_array& vertices, vertex start_index = 0)
    {
        const auto& row = adjacency_matrix[v];
        vertex_array C = {};
        for (vertex i = start_index; i < num_vertices; ++i)
        {
            if (row[i] > 0 && std::find(vertices.cbegin(), vertices.cend(), i) != vertices.cend()) { C.push_back(i); }
        }
        return C;
    }

    inline std::map<vertex, int> get_color_sets_in_range(const vertex_array& vertices)
    {
        auto size = vertices.size();
        assert(size != 0);
        std::map<vertex, int> colors;

        for (const auto& vertex : vertices)
        {
            std::vector<int> neighbour_colors;
            for (const auto& neighbour : get_connected(vertex, vertices))
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

    inline std::map<vertex, int> get_color_sets(const vertex_array& vertices)
    {
        auto size = vertices.size();
        assert(size != 0);
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

    inline std::vector<vertex_array> get_independent_sets(const std::map<vertex, int>& color_sets = {}, int colors_num = 0)
    {
        assert(colors_num != 0);
        std::vector<vertex_array> independent_sets(colors_num, vertex_array{});
        for (const auto& vertex_color_pair : color_sets)
        {
            // colors start from 1, not 0:
            independent_sets[vertex_color_pair.second-1].emplace_back(vertex_color_pair.first);
        }
        return independent_sets;
    }

    // tuple of (index of violated set, "weight" of violated set)
    inline std::tuple<int, IloNum> most_violated(const std::vector<vertex_array>& independent_sets, const std::vector<IloNum>& weights)
    {
        IloNum weight_of_most_violated = -1;
        int index_of_most_violated = -1;
        for (int i = 0, size = independent_sets.size(); i < size; ++i)
        {
            IloNum curr_set_weight = 0.;
            for (const auto& vertex : independent_sets[i]) { curr_set_weight += weights[vertex]; }

            if (curr_set_weight > weight_of_most_violated) // TODO: add proper ">" operation for doubles
            {
                weight_of_most_violated = curr_set_weight;
                index_of_most_violated = i;
            }
        }
        return std::make_tuple(index_of_most_violated, weight_of_most_violated);
    }

    inline std::vector<vertex_array> find_all_disconnected(const vertex_array& vertices)
    {
        std::vector<vertex_array> out{};
        for (const auto& curr_vertex : vertices)
        {
            for (int i = 0, size = vertices.size(); i < size; ++i)
            {
                if (curr_vertex != vertices[i] && adjacency_matrix[curr_vertex][vertices[i]] == 0)
                {
                    out.emplace_back(vertex_array({curr_vertex, vertices[i]}));
                }
            }
        }
        return out;
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
    inline bool is_almost_equal(T a, T b, int units_in_last_place = 2)
    {
        return std::abs(a - b) <= std::numeric_limits<T>::epsilon()
                                  * std::max(std::abs(a), std::abs(b))
                                  * units_in_last_place
               || std::abs(a - b) < std::numeric_limits<T>::min(); // subnormal result
    }

    #define ERROR_OUT(msg) std::cerr << "---\n" << msg << "\n---" << std::endl;
    #define ILOEXCEPTION_CATCH() \
    catch (const IloException& e) \
    { \
        std::string msg(e.getMessage()); \
        ERROR_OUT(msg); \
        std::exit(EXIT_FAILURE); \
    }

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

        auto independent_sets = get_independent_sets(color_sets, colors_num);
        for (const auto& set : independent_sets)
        {
            IloExpr expr(env);
            for (const auto& vertex : set)
            {
                expr += vars[vertex];
            }
            constraints.add(IloConstraint(expr <= 1.0));
        }
//        for (int row_num = 0, size = adj_m.size(); row_num < size; ++row_num)
//        {
//            for (int i = 0; i < num_vertices; ++i)
//            {
//                if (row_num != i && adj_m[row_num][i] == 0)
//                {
//                    IloExpr expr(env);
//                    expr += vars[row_num] + vars[i];
//                    constraints.add(IloConstraint(expr <= 1.0));
//                }
//            }
//        }
        auto& model = get_cplex_model();
        model.add(get_cplex_objective());
        model.add(constraints);

//        get_cplex_algo().setOut(get_cplex_env().getNullStream());
    }

    std::tuple<std::vector<IloNum>, int> get_noninteger_values(const IloNumArray& values)
    {
        std::vector<IloNum> out{};
        IloNum max = -1.0;
        int index_of_max_noninteger = -1;
        out.reserve(num_vertices);
        for (int i = 0; i < num_vertices; i++)
        {
            const IloNum& value = values[i];
            if (!is_almost_equal(value, 0.0) && !is_almost_equal(value, 1.0))
            {
                out.emplace_back(value);
                if (value > max)
                {
                    index_of_max_noninteger = i;
                    max = value;
                }
            }
        }
        return std::make_tuple(out, index_of_max_noninteger);
    }

    std::tuple<vertex_array, std::vector<IloNum>> get_nonzero_values(const IloNumArray& values)
    {
        vertex_array indices{};
        indices.reserve(num_vertices);
        std::vector<IloNum> weights{};
        weights.reserve(num_vertices);
        for (int i = 0; i < num_vertices; i++)
        {
            const IloNum& value = values[i];
            if (!is_almost_equal(value, 0.0))
            {
                indices.emplace_back(i);
                weights.emplace_back(value);
            }
        }
        // by design: weights[i] corresponds to indices[i]
        assert(weights.size() == indices.size());
        return std::make_tuple(indices, weights);
    }

    static int global_ub = 0;

    // optimal solution will be stored in these variables:
    int max_clique_size = 0;
    IloIntArray max_clique_values(get_cplex_env());

    bool branch_and_bound();
    bool branch_and_cut();

    /**
     * @brief BnB main function to execute branching logic to find integer solution
     *
     * @param[out] objective_value  Function value. Also represents current best value found.
     * @param[out] optimal_values   Values array. Also represents current best solution.
     * @return true                 Solution that equals global UB is found
     * @return false                Otherwise
     */
    bool branch_and_bound() try
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
        if (max_clique_size >= current_obj_val) // no idea about correct upper bound for this method
            return false;

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
            if (branch_and_bound())
                return true;
            model.remove(c1);

            IloConstraint c2(expr <= 0.0);
            model.add(c2);
            if (branch_and_bound())
                return true;
            model.remove(c2);
        }
        else
        {
            auto intValues = vals.toIntArray();
            vertex_array vertices_to_check{};
            for (int i = 0; i < num_vertices; i++)
            {
                if (intValues[i] == 1)
                {
                    vertices_to_check.emplace_back(i);
                }
            }
            auto disconnected = find_all_disconnected(vertices_to_check);
            if (!disconnected.empty()) // not a real clique
            {
                auto& vars = get_X();
                IloConstraintArray constraints(env);
                for (const auto& vertex_pair : disconnected)
                {
                    IloExpr expr(env);
                    for (const auto& vertex : vertex_pair)
                    {
                        expr += vars[vertex];
                    }
                    constraints.add(IloConstraint(expr <= 1.0));
                }
                get_cplex_model().add(constraints);
                return branch_and_cut();
            }

            max_clique_size = current_obj_val;
            max_clique_values = intValues;
            if (max_clique_size == global_ub)
                return true; // helps to reduce unnecessary calculations
        }
        return false;
    } ILOEXCEPTION_CATCH()


    bool branch_and_cut() try
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

        auto& env = get_cplex_env();
        IloNumArray vals(env);
        cplex.getValues(vals, get_X());

        auto result = get_nonzero_values(vals);
        auto& vertex_indices = std::get<0>(result); // vertices
        auto color_sets = get_color_sets_in_range(vertex_indices);
        auto colors_num = std::max_element(color_sets.begin(), color_sets.end(),
                                           [](const auto& p1, const auto& p2)
        {
            return p1.second < p2.second;
        })->second;

        auto independent_sets = get_independent_sets(color_sets, colors_num);
        if (independent_sets.empty()) // heuristic found nothing
        {
            return branch_and_bound();
        }
        auto& weights = std::get<1>(result); // weights
        auto mv_result = most_violated(independent_sets, weights);
        auto index_of_violated_set = std::get<0>(mv_result);
        auto most_violated_set_weight = std::get<1>(mv_result);
        // what to do next?
        if (index_of_violated_set < 0 || most_violated_set_weight <= 1.0) // nothing found
        {
            // something like that is expected:
            return branch_and_bound();
        }


        // adding new constraint
        auto& vars = get_X();
        IloExpr expr(env);
        for (const auto& vertex : independent_sets[index_of_violated_set])
        {
            expr += vars[vertex];
        }
        get_cplex_model().add(IloConstraint(expr <= 1.0));
        return branch_and_cut();
    } ILOEXCEPTION_CATCH()
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
            num_vertices = std::atoi(parsed[2].c_str());
            adjacency_matrix.resize(num_vertices, vertex_array(num_vertices, 0));
        }
        if (l0.compare("e") == 0) // format: e <vertex1> <vertex2>
        {
            auto v1 = static_cast<vertex>(std::atoi(parsed[1].c_str())) - 1,
                 v2 = static_cast<vertex>(std::atoi(parsed[2].c_str())) - 1;
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

    auto color_sets = get_color_sets(all_vertices);
    auto colors_num = std::max_element(color_sets.begin(), color_sets.end(),
                                       [](const auto& p1, const auto& p2)
    {
        return p1.second < p2.second;
    })->second;
    set_up_cplex(adjacency_matrix, color_sets, colors_num);

    auto& cplex = get_cplex_algo();
    if (!cplex.solve())
    {
        ERROR_OUT("IloCplex::solve() failed");
        return 1;
    }
    global_ub = static_cast<int>(cplex.getObjValue());
    if (global_ub > colors_num) global_ub = colors_num; // better upper-bound

    branch_and_cut();
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
