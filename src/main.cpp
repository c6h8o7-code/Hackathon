#include "main.hpp"
#include <bits/stdc++.h>

char applicationName[128] = "LLL";
void RenderUI()
{
    ImGui::Begin(applicationName, nullptr, 0);
    ImGui::End();
}
int main(){
    func_void Render = RenderUI;
    runcode(Render);
}