#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>
#include <vector>
#include <queue>
#include <mutex>
#include <map>
#include <iostream>

namespace py = pybind11;

class HiveBus {
public:
    void publish(const std::string& topic, const std::string& message) {
        std::lock_guard<std::mutex> lock(mtx);
        if (subscribers.find(topic) != subscribers.end()) {
            for (const auto& sub_id : subscribers[topic]) {
                message_queues[sub_id].push({topic, message});
                if (message_queues[sub_id].size() > 1000) {
                    message_queues[sub_id].pop(); // Cap buffer
                }
            }
        }
    }

    void subscribe(const std::string& sub_id, const std::string& topic) {
        std::lock_guard<std::mutex> lock(mtx);
        subscribers[topic].push_back(sub_id);
    }

    std::vector<std::pair<std::string, std::string>> consume(const std::string& sub_id) {
        std::lock_guard<std::mutex> lock(mtx);
        std::vector<std::pair<std::string, std::string>> batch;
        auto& q = message_queues[sub_id];
        while (!q.empty()) {
            batch.push_back(q.front());
            q.pop();
        }
        return batch;
    }

    size_t get_queue_size(const std::string& sub_id) {
        std::lock_guard<std::mutex> lock(mtx);
        return message_queues[sub_id].size();
    }

private:
    struct Message {
        std::string topic;
        std::string payload;
    };
    std::mutex mtx;
    std::map<std::string, std::vector<std::string>> subscribers;
    std::map<std::string, std::queue<std::pair<std::string, std::string>>> message_queues;
};

PYBIND11_MODULE(hive_bus, m) {
    py::class_<HiveBus>(m, "HiveBus")
        .def(py::init<>())
        .def("publish", &HiveBus::publish)
        .def("subscribe", &HiveBus::subscribe)
        .def("consume", &HiveBus::consume)
        .def("get_queue_size", &HiveBus::get_queue_size);
}
