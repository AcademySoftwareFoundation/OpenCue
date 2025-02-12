
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.depend;

public class QueueDependOperation implements Runnable {

    private DependVisitor visitor;
    private Depend depend;

    public QueueDependOperation(Depend depend, DependVisitor visitor) {
        this.depend = depend;
        this.visitor = visitor;
    }

    @Override
    public void run() {
        depend.accept(visitor);
    }
}
