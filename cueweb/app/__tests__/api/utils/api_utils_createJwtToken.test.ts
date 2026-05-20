/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { loadServerEnvVars } from '@/app/utils/config';
import { createJwtToken } from '@/app/utils/api_utils';

interface JwtParams {
  sub: string;
  role: string;
  iat: number;
  exp: number;
}

// This test is in its own file because there were issues with the mock functions when these tests were in api_utils.tests.ts.
// Using jest.mock outside of describe() would cause createJwtToken to return undefined, and using jest.mock inside of describe() would
// cause 'TypeError: filename.functionname.mockReturnValu is not a function'
jest.mock('@/app/utils/config', () => ({
    loadServerEnvVars: jest.fn(),
  }));
describe('createJwtToken', () => {
    const originalDateNow = Date.now;

    beforeEach(() => {
      jest.clearAllMocks();
      (loadServerEnvVars as jest.Mock).mockReturnValue({ NEXT_JWT_SECRET: 'NEXT_JWT_SECRET' });
    });

    afterEach(() => {
      Date.now = originalDateNow;
    });
  
    it('should create a valid JWT token', () => {
      // Below is the expected token generated from createJwtToken. The expected token is generate
      // from: https://jwt.io/ using the payload below and the secret 'NEXT_JWT_SECRET'.
      const correctToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwicm9sZSI6ImFkbWluIiwiaWF0IjowLCJleHAiOjM2MDB9.ufO-E909jnVrowhB1ff1Yfxa4ykEchOprBqs4O-MAYs"
      // We need to set the date to 0 since that is the iat that the correctToken was generated with
      Date.now = jest.fn(() => 0);
      
      const jwtParams = {
        sub: 'user123', // Define a user id for the token
        role: 'admin', // Define a user role for the token
        iat: 0, // Define the issued at time
        exp: 3600, // Define the expiration time (1 hour from iat)
      }
  
      const token = createJwtToken(jwtParams);
  
      // We validate that the generated token from createJwtToken matches our expected token
      expect(token).toBe(correctToken);
    });
  });
