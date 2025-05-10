Feature: Hello World Endpoint

  Scenario: Accessing the root endpoint
    When I send a GET request to "/"
    Then the response status code should be 200
    And the response body should be JSON
    And the response JSON should be {"Hello": "World"}
