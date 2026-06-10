/**
 * @jest-environment jsdom
 */

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

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import * as getUtils from "@/app/utils/get_utils";
import ShowsPage from "@/app/shows/page";

// Factory mock avoids loading the real module's transitive imports.
jest.mock("@/app/utils/get_utils", () => ({ getShows: jest.fn() }));

// next/link needs App Router context; passthrough <a> keeps the test scoped.
jest.mock("next/link", () => ({
  __esModule: true,
  default: ({ children, ...props }: { children: React.ReactNode }) =>
    require("react").createElement("a", props, children),
}));

const getShows = getUtils.getShows as jest.Mock;

describe("ShowsPage", () => {
  beforeEach(() => {
    getShows.mockReset();
    getShows.mockResolvedValue([]);
  });

  it("loads shows on mount and refetches when Refresh is clicked", async () => {
    render(<ShowsPage />);

    await waitFor(() => expect(getShows).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: /refresh/i }));

    await waitFor(() => expect(getShows).toHaveBeenCalledTimes(2));
  });
});
