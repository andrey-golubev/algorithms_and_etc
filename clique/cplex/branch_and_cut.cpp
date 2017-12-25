#define ILOUSESTL
using namespace std;
#include "ilocplex.h"

#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <cstdint>
#include <vector>
#include <list>
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
    inline vertex_array get_connected(vertex v)
    {
        const auto& row = adjacency_matrix[v];
        vertex_array C = {};
        for (vertex i = 0; i < num_vertices; ++i)
        {
            if (row[i] > 0) { C.push_back(i); }
        }
        return C;
    }
    inline vertex_array get_connected(vertex v, const vertex_array& vertices)
    {
        const auto& row = adjacency_matrix[v];
        vertex_array C = {};
        for (const auto& other_v : vertices)
        {
            if (v != other_v && row[other_v] > 0)
            {
                C.push_back(other_v);
            }
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

    inline std::vector<vertex_array> get_independent_sets_internal(const std::map<vertex, int>& color_sets = {}, int colors_num = 0)
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

    inline std::vector<vertex_array> get_independent_sets(const vertex_array& vertices)
    {
        auto color_sets = get_color_sets_in_range(vertices);
        auto colors_num = std::max_element(color_sets.begin(), color_sets.end(),
                                           [](const auto& p1, const auto& p2)
        {
            return p1.second < p2.second;
        })->second;
        return get_independent_sets_internal(color_sets, colors_num);
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

        int size = vertices.size();
        for (int i = 0; i < size; ++i)
        {
            for (int j = i + 1; j < size; ++j)
            {
                if (vertices[i] != vertices[j] && adjacency_matrix[vertices[i]][vertices[j]] == 0)
                {
                    out.emplace_back(vertex_array({vertices[i], vertices[j]}));
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
    inline bool are_equal(T a, T b, int units_in_last_place = 2)
    {
        return std::abs(a - b) <= std::numeric_limits<T>::epsilon()
                                  * std::max(std::abs(a), std::abs(b))
                                  * units_in_last_place
               || std::abs(a - b) < std::numeric_limits<T>::min(); // subnormal result
    }

    template<typename T>
    inline bool are_almost_equal(T a, T b, T epsilon)
    {
        return are_equal(std::abs(a - b), epsilon);
    }

    static constexpr char constraints_file[] = "constraints.log";
    #define ERROR_OUT(msg) std::cerr << "---\n" << msg << "\n---" << std::endl;
    #define ILOEXCEPTION_CATCH() \
    catch (const IloException& e) \
    { \
        ERROR_OUT(e.getMessage()); \
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
            if (are_equal(vertices[i], 1.0))
            {
                s.append(std::to_string(i + 1));
                s.append(" ");
            }
        }
        return s;
    }

    inline void throw_on_timeout() noexcept(false)
    {
        auto elapsed = std::chrono::duration_cast<std::chrono::duration<double>>(_chrono::now() - start_time);
        if (elapsed.count() > time_limit)
        {
            throw std::runtime_error("Out of time");
        }
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
        return cplex_algo;
    }

    static inline IloObjective& get_cplex_objective()
    {
        static IloObjective obj_function = IloMaximize(get_cplex_env());
        return obj_function;
    }

    static std::string status_to_string(IloAlgorithm::Status sts)
    {
        switch (sts)
        {
        case IloAlgorithm::Status::Unknown: return std::string("Unknown");
        case IloAlgorithm::Status::Feasible: return std::string("Feasible");
        case IloAlgorithm::Status::Optimal: return std::string("Optimal");
        case IloAlgorithm::Status::Infeasible: return std::string("Infeasible");
        case IloAlgorithm::Status::Unbounded: return std::string("Unbounded");
        case IloAlgorithm::Status::InfeasibleOrUnbounded: return std::string("InfeasibleOrUnbounded");
        case IloAlgorithm::Status::Error: return std::string("Error");
        }
    }

    template<typename ConditionCallable, typename T>
    static void print_cplex(ConditionCallable condition, T file_name)
    {
        std::ofstream stream(file_name);
        auto& model = get_cplex_model();
        for (IloModel::Iterator it(model); it.ok(); ++it)
        {
            IloExtractable e = *it;
            if (condition(e))
            {
                stream << e << std::endl;
            }
        }
    }

    static void print_cplex_constraints()
    {
        print_cplex([] (const IloExtractable& e) { return e.isConstraint(); }, constraints_file);
    }

    static void print_cplex_objective()
    {
        print_cplex([] (const IloExtractable& e) { return e.isObjective(); }, "objective.log");
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

        auto independent_sets = get_independent_sets_internal(color_sets, colors_num);
        for (const auto& set : independent_sets)
        {
            IloExpr expr(env);
            for (const auto& vertex : set)
            {
                expr += vars[vertex];
            }
            constraints.add(IloConstraint(expr <= 1.0));
        }
        get_cplex_model().add(get_cplex_objective());
        get_cplex_model().add(constraints);

        get_cplex_algo().setParam(IloCplex::Param::RootAlgorithm, IloCplex::Concurrent);
        get_cplex_algo().setOut(get_cplex_env().getNullStream());
    }

    bool solve_cplex()
    {
        auto& cplex = get_cplex_algo();
        if (!cplex.solve())
        {
            auto sts = cplex.getStatus();
            if (sts == IloAlgorithm::Status::Infeasible) // infeasible means that there are such constraints that couldn't co-exist. such branch should be dropped
            {
                return false;
            }
            ERROR_OUT("IloCplex::solve() failed with staus: " << status_to_string(sts) << std::endl << "constraints would be written into: " << constraints_file);
            print_cplex_constraints();
            std::exit(EXIT_FAILURE);
        }
        return true;
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
            if (!are_equal(value, 0.0) && !are_equal(value, 1.0))
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
            if (!are_equal(value, 0.0))
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
    IloNumArray max_clique_values(get_cplex_env());
    std::string graph_file_name;

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
    bool branch_and_bound() try // TODO: store integer constrains somewhere and delete them when going into branch_and_cut
    {
        if (!solve_cplex())
            return false;

        throw_on_timeout();

        auto& cplex = get_cplex_algo();

        // if non-integer solution is worse than current best - return immediately
        auto current_obj_val = static_cast<int>(cplex.getObjValue());
        if (max_clique_size >= current_obj_val) // TODO: no idea about correct upper bound for branch-and-cut
            return false;

        auto& env = get_cplex_env();
        IloNumArray vals(env);
        cplex.getValues(vals, get_X());
        auto result = get_noninteger_values(vals);
        auto nonInts = std::get<0>(result);
        if (!nonInts.empty())
        {
            auto& model = get_cplex_model();
            auto index_to_branch = std::get<1>(result);
            IloExpr expr(env);
            auto& vars = get_X();
            expr += vars[index_to_branch];
            IloConstraint c1(expr >= 1.0);
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
            vertex_array vertices_to_check{};
            for (int i = 0; i < num_vertices; i++)
            {
                if (are_equal(vals[i], 1.0))
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
                branch_and_cut();
                return false;
//                return branch_and_cut();
            }

            if (max_clique_size >= current_obj_val)
                return false;

            max_clique_size = current_obj_val;
            max_clique_values = vals;
            if (max_clique_size == global_ub)
                return true; // helps to reduce unnecessary calculations
        }
        return false;
    } ILOEXCEPTION_CATCH()


    bool branch_and_cut() try
    {
        if (!solve_cplex())
            return false;

        auto& cplex = get_cplex_algo();
        // if non-integer solution is worse than current best - return immediately
        auto current_obj_val = static_cast<int>(cplex.getObjValue());
        if (max_clique_size >= current_obj_val) // TODO: no idea about correct upper bound for branch-and-cut
            return false;

        throw_on_timeout();

        auto& env = get_cplex_env();
        IloNumArray vals(env);
        cplex.getValues(vals, get_X());

        auto result = get_nonzero_values(vals);
        auto independent_sets = get_independent_sets(std::get<0>(result));
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

#define TO_DEBUG 0 // TODO: debug wtf is happening

    bool real_branch_and_cut() try
    {
        if (!solve_cplex())
            return false;

        auto& cplex = get_cplex_algo();

        // if non-integer solution is worse than current best - return immediately
        // difficult objective value calculation:
        auto obj_val_as_double = cplex.getObjValue();
        auto current_obj_val = static_cast<int>(cplex.getObjValue());
        if (are_equal(obj_val_as_double, double(current_obj_val + 1)))
            current_obj_val++;
        if (max_clique_size >= current_obj_val) // TODO: no idea about correct upper bound for branch-and-cut
            return false;

        throw_on_timeout();

        auto& env = get_cplex_env();
        auto& model = get_cplex_model();

        int add_cut_counter = 0;
        int objective_nonchanges_counter = 0;

        // adding cuts part:
        while(true) // loop until no violations found or heuristic fails
        {
            IloNumArray intermediate_vals(env);
            cplex.getValues(intermediate_vals, get_X());
            auto result = get_nonzero_values(intermediate_vals);
            auto independent_sets = get_independent_sets(std::get<0>(result));
            if (independent_sets.empty()) // heuristic found no independent sets
            {
                break; // go to branching
            }

            auto& weights = std::get<1>(result); // weights
            auto mv_result = most_violated(independent_sets, weights);
            auto index_of_violated_set = std::get<0>(mv_result);
            auto most_violated_set_weight = std::get<1>(mv_result);
            if (index_of_violated_set < 0 || most_violated_set_weight <= 1.0) // none violated constraints found
            {
                break; // go to branching
            }

            auto prev_obj_val = cplex.getObjValue();

            // adding new constraint:
            auto& vars = get_X();
            IloExpr expr(env);
            for (const auto& vertex : independent_sets[index_of_violated_set])
            {
                expr += vars[vertex];
            }
            model.add(IloConstraint(expr <= 1.0));
            if (!solve_cplex()) // solve with newly added constraint - return to the beginning of the loop
                return false;

            add_cut_counter++;
            if (add_cut_counter >= num_vertices)// * 2 / 3)
            {
                // probably spent too much time on adding constraints
                // added order of num_vertices amount of constraints - force branching
                break;
            }

            if (are_almost_equal(prev_obj_val, cplex.getObjValue(), 0.01))
            {
                objective_nonchanges_counter++;
            }
            if (objective_nonchanges_counter >= 7)
            {
                break; // go to branch. objective value didn't change for long enough
            }
        }

        // branching part:
        throw_on_timeout();

        // ! cplex already solved the problem
        IloNumArray vals(env);
        cplex.getValues(vals, get_X());
        auto result = get_noninteger_values(vals);
        auto nonInts = std::get<0>(result);
        if (!nonInts.empty())
        {
            auto& model = get_cplex_model();
            auto index_to_branch = std::get<1>(result);
            IloExpr expr(env);
            auto& vars = get_X();
            expr += vars[index_to_branch];
            IloConstraint c1(expr >= 1.0);
            model.add(c1);
            if (real_branch_and_cut()) // branching part
                return true;
            model.remove(c1);

            IloConstraint c2(expr <= 0.0);
            model.add(c2);
            if (real_branch_and_cut()) // branching part
                return true;
            model.remove(c2);
        }
        else
        {
#if TO_DEBUG == 1
            vertex_array all_vertices(num_vertices, 0);
#endif
            vertex_array vertices_to_check{};
            for (int i = 0; i < num_vertices; i++)
            {
#if TO_DEBUG == 1
                all_vertices[i] = vals[i];
#endif
                if (are_equal(vals[i], 1.0))
                {
                    vertices_to_check.emplace_back(i);
                }
            }
            auto disconnected = find_all_disconnected(vertices_to_check);
            if (!disconnected.empty()) // not a real clique
            {
                auto& vars = get_X();
                IloConstraintArray constraints(env);
                for (const auto& pair : disconnected) // consider to add only the best suitable constraint
                {
                    IloExpr expr(env);
                    expr += vars[pair[0]];
                    expr += vars[pair[1]];
//                    constraints.add(IloRange(env, vars[pair[0]] +  vars[pair[1]], 1.0));
                    constraints.add(IloConstraint(expr <= 1.0));
                }
                get_cplex_model().add(constraints);
                return real_branch_and_cut();
            }

#if TO_DEBUG != 1
            if (current_obj_val != vertices_to_check.size())
            {
                static int print_count = 1;
                print_cplex_objective();
                std::ofstream stream(std::string("vars_").append(graph_file_name).append(".log"));
                print_count++;
                for (int i = 0; i < num_vertices; i++)
                {
                    stream << "IloVariable(" << i + 2 << "): " << vals[i] << std::endl;
                }
            }
#endif

            // found a clique:
            if (max_clique_size >= current_obj_val)
                return false;
            max_clique_size = current_obj_val;
            max_clique_values = vals;
            if (max_clique_size == global_ub)
                return true; // helps to reduce unnecessary calculations
        }

        return false;
    } ILOEXCEPTION_CATCH()

}

int main(int argc, char* argv[]) try
{
    if (argc < 3)
    {
        ERROR_OUT("Command-line arguments: <file> <time limit>. Ex: ./mlp graph.clq 1000");
        return 1;
    }
    graph_file_name = std::string(argv[1]);
    std::ifstream f(graph_file_name);
    if (!f.good())
    {
        ERROR_OUT("File is unreachable/not found");
        return 1;
    }
    time_limit = std::atof(argv[2]); // in seconds
    if (time_limit <= 0)
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
    real_branch_and_cut();

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
