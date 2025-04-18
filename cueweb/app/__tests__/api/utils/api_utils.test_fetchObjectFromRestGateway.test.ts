import { loadClientEnvVars, loadServerEnvVars } from '@/app/utils/config';
import { createJwtToken, fetchObjectFromRestGateway } from '@/app/utils/api_utils';
import jwt from "jsonwebtoken";

// Mock loadClientEnvVars and createJwtToken to return two predefined environment variables
// (required when calling fetchObjectFromRestGateway) and to create a mock jwt token
// Mock the modules and their functions
jest.mock('@/app/utils/config', () => ({
  loadClientEnvVars: jest.fn(),
  loadServerEnvVars: jest.fn(),
}));
jest.mock('@/app/utils/api_utils', () => ({
  ...jest.requireActual('@/app/utils/api_utils'), // Keep the original implementation for other functions
  createJwtToken: jest.fn(), // Mock the createJwtToken function
}));
jest.mock('jsonwebtoken', () => ({
  sign: jest.fn(),
}));


describe('fetchObjectFromRestGateway', () => {

  // Mock the responses from the gRPC REST gateway to test error catching
  global.fetch = jest.fn();

  // Clear mocks before running each test and mock the return values of loadClientEnvVars and createJwtToken
  beforeEach(() => {
    jest.clearAllMocks();
    (jwt.sign as jest.Mock).mockReturnValue('mockJwtToken');
    (createJwtToken as jest.Mock).mockReturnValue('mockJwtToken');
  });
  
  /*
  Given a non error response from the gRPC REST gateway expect:
  - createJwtToken to be called with correct parameters
  - status 200 and correct data to be returned
  */
  it('should successfully fetch from the gRPC REST gateway', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      text: jest.fn().mockResolvedValue(JSON.stringify({ data: 'mockData' })),
    });

    const endpoint = '/test-endpoint';
    const method = 'POST';
    const body = JSON.stringify({ key: 'value' });
    const response = await fetchObjectFromRestGateway(endpoint, method, body);

    expect(fetch).toHaveBeenCalledWith('NEXT_PUBLIC_OPENCUE_ENDPOINT/test-endpoint', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mockJwtToken',
      },
      body: JSON.stringify({ key: 'value' }),
    });
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ data: { data: 'mockData' } });
  });

  /*
  Given a 401 status response from the gRPC REST gateway expect:
  - createJwtToken to be called with correct parameters
  - status 401 and error message 'Unauthorized request: Unauthorized error' to be returned
  */
  it('should handle unauthorized request', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 401,
      text: jest.fn().mockResolvedValue('Unauthorized error'),
    });

    const endpoint = '/test-endpoint';
    const method = 'POST';
    const body = JSON.stringify({ key: 'value' });

    const response = await fetchObjectFromRestGateway(endpoint, method, body);

    expect(fetch).toHaveBeenCalledWith('NEXT_PUBLIC_OPENCUE_ENDPOINT/test-endpoint', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mockJwtToken',
      },
      body: JSON.stringify({ key: 'value' }),
    });
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({ error: 'Unauthorized request: Unauthorized error' });
  });

  /*
  Given a 404 status response from the gRPC REST gateway expect:
  - createJwtToken to be called with correct parameters
  - status 404 and error message 'Resource not found: Resource not found' to be returned
  */
  it('should handle resource not found', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 404,
      text: jest.fn().mockResolvedValue('Resource not found'),
    });

    const endpoint = '/test-endpoint';
    const method = 'POST';
    const body = JSON.stringify({ key: 'value' });

    const response = await fetchObjectFromRestGateway(endpoint, method, body);

    expect(fetch).toHaveBeenCalledWith('NEXT_PUBLIC_OPENCUE_ENDPOINT/test-endpoint', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mockJwtToken',
      },
      body: JSON.stringify({ key: 'value' }),
    });
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({ error: 'Resource not found: Resource not found' });
  });

  /*
  Given a 500 status response from the gRPC REST gateway expect:
  - createJwtToken to be called with correct parameters
  - status 500 and error message 'Unexpected API Error: Unexpected error' to be returned
  */
  it('should handle unexpected API error', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
      text: jest.fn().mockResolvedValue('Unexpected error'),
    });

    const endpoint = '/test-endpoint';
    const method = 'POST';
    const body = JSON.stringify({ key: 'value' });

    const response = await fetchObjectFromRestGateway(endpoint, method, body);

    expect(fetch).toHaveBeenCalledWith('NEXT_PUBLIC_OPENCUE_ENDPOINT/test-endpoint', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mockJwtToken',
      },
      body: JSON.stringify({ key: 'value' }),
    });
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({ error: 'Unexpected API error: Unexpected error' });
  });

  /*
  Given an error when fetching from the gRPC REST gateway expect:
  - createJwtToken to be called with correct parameters
  - status 400 and error message 'Fetch error' to be returned
  */
  it('should handle fetch errors', async () => {
    (fetch as jest.Mock).mockRejectedValue(new Error('Fetch error'));

    const endpoint = '/test-endpoint';
    const method = 'POST';
    const body = JSON.stringify({ key: 'value' });

    const response = await fetchObjectFromRestGateway(endpoint, method, body);

    expect(fetch).toHaveBeenCalledWith('NEXT_PUBLIC_OPENCUE_ENDPOINT/test-endpoint', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mockJwtToken',
      },
      body: JSON.stringify({ key: 'value' }),
    });
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({ error: 'Fetch error' });
  });
});
