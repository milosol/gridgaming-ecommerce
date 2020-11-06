$(function(){
    $("#div_winner input").change(function(){
        winner = $("#in_winner").val();
        if(winner < 1){
            $("#div_winner").addClass('error')
        }else{
            $("#div_winner").removeClass('error')
        }
        set_settings();
    })
    $('#add_tags').tagsInput({
        onChange: ()=>{
            set_settings();
        }
    });
})
function get_actions(){
    res = {}
    winner = $("#in_winner").val();
    res.fe = true;
    res.tags = $('#add_tags').val();
    if(winner > 0) res.winner = winner
    else res.winner = ''
    return res
}